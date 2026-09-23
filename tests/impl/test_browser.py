from impl.browser import _rmtree
from os import chmod, mkdir
from os.path import join, exists
from stat import S_IREAD
from tempfile import mkdtemp
from unittest import TestCase

class RmtreeTest(TestCase):
    def test_read_only_file(self):
        tmp_dir = mkdtemp()
        sub_dir = join(tmp_dir, 'blocks')
        mkdir(sub_dir)
        read_only_file = join(sub_dir, '_README')
        with open(read_only_file, 'w') as f:
            f.write('x')
        chmod(read_only_file, S_IREAD)
        _rmtree(tmp_dir)
        self.assertFalse(exists(tmp_dir))
