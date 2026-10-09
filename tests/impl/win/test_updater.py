from impl.win.registry import delete_key
from impl.win.updater import (
    _delete_dir, _find_com_registrations, _find_progids,
    _find_tasks_recursively, _is_omaha3_service, _is_omaha4_service
)
from os import environ, mkdir
from os.path import exists, join
from tempfile import TemporaryDirectory
from threading import Timer
from unittest import TestCase
from unittest.mock import patch
from winreg import HKEY_CURRENT_USER, CreateKey, SetValue, REG_SZ

KEY = r'SOFTWARE\brave-manager-test'

class FindComRegistrationsTest(TestCase):
    def setUp(self):
        # Like Omaha 3: one proxy/stub for all interfaces, and a COM server.
        self._add_class('{A}', 'InprocServer32', r'C:\Update\1.3\psuser.dll')
        self._add_class('{B}', 'LocalServer32', r'"C:\Update\Update.exe" /c')
        self._add_class('{C}', 'InprocServer32', r'C:\Other\psuser.dll')
        self._add_class('{D}', 'InprocServer32', r'C:\UpdateDev\psuser.dll')
        self._add_interface('{1}', '{a}')
        self._add_interface('{2}', '{C}')
        with CreateKey(HKEY_CURRENT_USER, KEY + r'\Interface\{3}'):
            pass
    def tearDown(self):
        delete_key(HKEY_CURRENT_USER, KEY)
    def test_find_com_registrations(self):
        keys = _find_com_registrations(HKEY_CURRENT_USER, KEY, r'C:\Update')
        self.assertEqual(
            [KEY + r'\CLSID\{A}', KEY + r'\CLSID\{B}', KEY + r'\Interface\{1}'],
            sorted(keys)
        )
    def test_no_classes(self):
        delete_key(HKEY_CURRENT_USER, KEY)
        self.assertEqual(
            [], _find_com_registrations(HKEY_CURRENT_USER, KEY, r'C:\Update')
        )
    def _add_class(self, clsid, server, path):
        server_key = KEY + rf'\CLSID\{clsid}\{server}'
        SetValue(HKEY_CURRENT_USER, server_key, REG_SZ, path)
    def _add_interface(self, iid, proxy_stub):
        proxy_stub_key = KEY + rf'\Interface\{iid}\ProxyStubClsid32'
        SetValue(HKEY_CURRENT_USER, proxy_stub_key, REG_SZ, proxy_stub)

class FindProgidsTest(TestCase):
    def setUp(self):
        for progid in (
            'BraveSoftwareUpdate.Update3COMClassUser',
            'BraveSoftwareUpdate.Update3COMClassUser.1.0',
            'bravesoftwareupdate.PolicyStatusUser',
            'BraveSoftwareUpdater.Other',
            'Other'
        ):
            with CreateKey(HKEY_CURRENT_USER, rf'{KEY}\{progid}\CLSID'):
                pass
    def tearDown(self):
        delete_key(HKEY_CURRENT_USER, KEY)
    def test_find_progids(self):
        keys = _find_progids(HKEY_CURRENT_USER, KEY, 'BraveSoftwareUpdate.')
        self.assertEqual([
            KEY + r'\BraveSoftwareUpdate.Update3COMClassUser',
            KEY + r'\BraveSoftwareUpdate.Update3COMClassUser.1.0',
            KEY + r'\bravesoftwareupdate.PolicyStatusUser'
        ], sorted(keys))

class FindTasksRecursivelyTest(TestCase):
    # Maps each folder to its tasks and subfolders, like list_folder(...). The
    # booleans say whether a task runs as the current user.
    FOLDERS = {
        r'\C': ([(r'\C\mine', True)], [r'\C\A', r'\C\B']),
        r'\C\A': ([(r'\C\A\mine', True)], []),
        r'\C\B': ([(r'\C\B\other', False)], [])
    }
    def test_user(self):
        # \C\B holds another user's task. So it and \C must stay:
        self.assertEqual(
            ([r'\C\A\mine', r'\C\mine'], [r'\C\A']), self._find(r'\C', False)
        )
    def test_system(self):
        self.assertEqual(
            (
                [r'\C\A\mine', r'\C\B\other', r'\C\mine'],
                [r'\C\A', r'\C\B', r'\C']
            ),
            self._find(r'\C', True)
        )
    def test_no_folder(self):
        self.assertEqual(([], []), self._find(r'\X', False))
    def _find(self, folder, is_system_level):
        with patch('impl.win.task_scheduler.list_folder', self.FOLDERS.get):
            return _find_tasks_recursively(folder, is_system_level)

class IsServiceTest(TestCase):
    BRAVE_SOFTWARE = join(environ['PROGRAMFILES(X86)'], 'BraveSoftware')
    def test_omaha3_by_name(self):
        # Like the services that Omaha 4's integration tests create:
        self.assertTrue(_is_omaha3_service(
            'bravem', 'Brave Update Service', r'C:\temp\temp.exe'
        ))
    def test_omaha3_by_path(self):
        # With a localized display name:
        self.assertTrue(_is_omaha3_service(
            'brave', 'Service Brave Update (brave)',
            rf'"{self.BRAVE_SOFTWARE}\Update\BraveUpdate.exe" /svc'
        ))
    def test_omaha4(self):
        args = (
            'BraveUpdaterService155.1.99.19', 'BraveUpdater Service',
            rf'"{self.BRAVE_SOFTWARE}\BraveUpdater\155.1.99.19\updater.exe" '
            '--system --windows-service'
        )
        self.assertTrue(_is_omaha4_service(*args))
        self.assertFalse(_is_omaha3_service(*args))
    def test_browser(self):
        args = (
            'BraveElevationService',
            'Brave Elevation Service (BraveElevationService)',
            r'"C:\Program Files\BraveSoftware\Brave-Browser\Application'
            r'\155.1.97.56\elevation_service.exe"'
        )
        self.assertFalse(_is_omaha3_service(*args))
        self.assertFalse(_is_omaha4_service(*args))

class DeleteDirTest(TestCase):
    def test_retries_while_file_is_locked(self):
        with TemporaryDirectory() as tmp_dir:
            path = join(tmp_dir, 'BraveUpdater')
            locked_file = self._create_locked_file(path)
            Timer(1, locked_file.close).start()
            _delete_dir(path, timeout_seconds=10)
            self.assertFalse(exists(path))
    def test_raises_after_timeout(self):
        with TemporaryDirectory() as tmp_dir:
            path = join(tmp_dir, 'BraveUpdater')
            with self._create_locked_file(path):
                with self.assertRaises(PermissionError):
                    _delete_dir(path, timeout_seconds=1)
    def _create_locked_file(self, dir_path):
        mkdir(dir_path)
        # Python opens files without FILE_SHARE_DELETE:
        return open(join(dir_path, 'updater.exe'), 'w')
