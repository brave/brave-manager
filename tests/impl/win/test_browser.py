from impl.win.browser import _get_architecture
from os.path import join
from tempfile import TemporaryDirectory
from unittest import TestCase

class GetArchitectureTest(TestCase):
    def test_x64(self):
        self._check(0x8664, 'x64')
    def test_x86(self):
        self._check(0x014c, 'x86')
    def test_arm64(self):
        self._check(0xaa64, 'arm64')
    def test_unknown(self):
        with self.assertRaises(ValueError):
            self._check(0x8664, None, signature=b'\xcf\xfa\xed\xfe')
    def _check(self, machine, expected, signature=b'PE\0\0'):
        pe_header_offset = 0x40
        contents = b'MZ' + bytes(0x3c - 2) \
            + pe_header_offset.to_bytes(4, 'little') \
            + bytes(pe_header_offset - 0x40) \
            + signature + machine.to_bytes(2, 'little')
        with TemporaryDirectory() as tmp_dir:
            path = join(tmp_dir, 'brave.exe')
            with open(path, 'wb') as f:
                f.write(contents)
            self.assertEqual(expected, _get_architecture(path))
