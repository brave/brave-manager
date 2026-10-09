from impl.win.registry import delete_key, list_subkeys
from impl.win.updater import (
    _delete_com_registrations, _delete_dir, _delete_progids
)
from os import mkdir
from os.path import exists, join
from tempfile import TemporaryDirectory
from threading import Timer
from unittest import TestCase
from winreg import HKEY_CURRENT_USER, CreateKey, SetValue, REG_SZ

KEY = r'SOFTWARE\brave-manager-test'

class DeleteComRegistrationsTest(TestCase):
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
    def test_delete_com_registrations(self):
        _delete_com_registrations(HKEY_CURRENT_USER, KEY, r'C:\Update')
        self.assertEqual(['{C}', '{D}'], self._list(r'\CLSID'))
        self.assertEqual(['{2}', '{3}'], self._list(r'\Interface'))
    def test_no_classes(self):
        delete_key(HKEY_CURRENT_USER, KEY)
        _delete_com_registrations(HKEY_CURRENT_USER, KEY, r'C:\Update')
    def _add_class(self, clsid, server, path):
        server_key = KEY + rf'\CLSID\{clsid}\{server}'
        SetValue(HKEY_CURRENT_USER, server_key, REG_SZ, path)
    def _add_interface(self, iid, proxy_stub):
        proxy_stub_key = KEY + rf'\Interface\{iid}\ProxyStubClsid32'
        SetValue(HKEY_CURRENT_USER, proxy_stub_key, REG_SZ, proxy_stub)
    def _list(self, subkey):
        return sorted(list_subkeys(HKEY_CURRENT_USER, KEY + subkey))

class DeleteProgidsTest(TestCase):
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
    def test_delete_progids(self):
        _delete_progids(HKEY_CURRENT_USER, KEY, 'BraveSoftwareUpdate.')
        self.assertEqual(
            ['BraveSoftwareUpdater.Other', 'Other'],
            sorted(list_subkeys(HKEY_CURRENT_USER, KEY))
        )

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
