from impl.win.updater import _delete_dir
from os import mkdir
from os.path import exists, join
from tempfile import TemporaryDirectory
from threading import Timer
from unittest import TestCase

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
