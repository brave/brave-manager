from impl.mac.browser import _get_architecture
from os.path import join
from tempfile import TemporaryDirectory
from unittest import TestCase

class GetArchitectureTest(TestCase):
    def test_x64(self):
        self._check(b'\xcf\xfa\xed\xfe\x07\x00\x00\x01', 'x64')
    def test_arm64(self):
        self._check(b'\xcf\xfa\xed\xfe\x0c\x00\x00\x01', 'arm64')
    def test_universal(self):
        self._check(b'\xca\xfe\xba\xbe\x00\x00\x00\x02', 'universal')
    def test_unknown(self):
        with self.assertRaises(ValueError):
            self._check(b'MZ\x90\x00\x03\x00\x00\x00', None)
    def _check(self, header, expected):
        with TemporaryDirectory() as tmp_dir:
            path = join(tmp_dir, 'executable')
            with open(path, 'wb') as f:
                f.write(header)
            self.assertEqual(expected, _get_architecture(path))
