from unittest import TestCase
from impl.util import human_readable_size

class HumanReadableSizeTest(TestCase):
    def test_zero_bytes(self):
        self._check(0, '0 B')
    def test_bytes(self):
        self._check(123, '123 B')
    def test_kb(self):
        self._check(123_456, '123 KB')
    def test_mb(self):
        self._check(123_456 * 10 ** 3, '123 MB')
    def test_few_gb(self):
        self._check(1_234 * 10 ** 6, '1.23 GB')
    def test_many_gb(self):
        self._check(123_456 * 10 ** 6, '123 GB')
    def test_tb(self):
        self._check(123_456_789 * 10 ** 6, '123 TB')
    def _check(self, size, expected):
        self.assertEqual(expected, human_readable_size(size))
