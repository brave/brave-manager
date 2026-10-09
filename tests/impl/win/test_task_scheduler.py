from impl.win.task_scheduler import list_folder, delete_task, delete_folder
from pywintypes import com_error
from subprocess import run
from unittest import TestCase

FOLDER = r'\brave-manager-test'

class TaskSchedulerTest(TestCase):
    def setUp(self):
        # Creating a task also creates its folders:
        self._create_task(FOLDER + r'\task')
        self._create_task(FOLDER + r'\sub\task')
    def tearDown(self):
        for path in (FOLDER + r'\sub\task', FOLDER + r'\task'):
            run(['schtasks', '/Delete', '/TN', path, '/F'], capture_output=True)
        for path in (FOLDER + r'\sub', FOLDER):
            if list_folder(path) is not None:
                delete_folder(path)
    def test_list_folder(self):
        self.assertEqual(
            ([(FOLDER + r'\task', True)], [FOLDER + r'\sub']),
            list_folder(FOLDER)
        )
        self.assertIsNone(list_folder(FOLDER + r'\x'))
    def test_delete(self):
        delete_task(FOLDER + r'\sub\task')
        delete_folder(FOLDER + r'\sub')
        self.assertEqual(([(FOLDER + r'\task', True)], []), list_folder(FOLDER))
    def test_delete_non_empty_folder(self):
        with self.assertRaises(com_error):
            delete_folder(FOLDER + r'\sub')
    def _create_task(self, path):
        # A one-off task at 00:00 today is in the past and never runs. /SD
        # would expect a localized date format, so we don't pass it.
        run([
            'schtasks', '/Create', '/TN', path, '/TR', 'cmd /c exit',
            '/SC', 'ONCE', '/ST', '00:00', '/F'
        ], check=True, capture_output=True)
