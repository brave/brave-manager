from impl.win.browser import _get_architecture, _read_tag, Brave, Origin
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

class ReadTagTest(TestCase):
    def test_read_tag(self):
        tag = 'appguid={C6CB981E-DB30-4876-8639-109F8933582C}' \
            '&appname=Brave-Browser-Nightly&needsadmin=prefers&ap=nightly' \
            '&installdataindex=default'
        with TemporaryDirectory() as tmp_dir:
            path = join(tmp_dir, 'BraveBrowserNightlySetup.exe')
            with open(path, 'wb') as f:
                f.write(b'MZ' + bytes(1000) + tag.encode() + bytes(10))
            self.assertEqual(tag, _read_tag(path))
    def test_no_tag(self):
        with TemporaryDirectory() as tmp_dir:
            path = join(tmp_dir, 'BraveBrowserUntaggedNightlySetup.exe')
            with open(path, 'wb') as f:
                f.write(b'MZ' + bytes(1000))
            with self.assertRaises(ValueError):
                _read_tag(path)

class AcceptsInstallerTest(TestCase):
    def test_nightly_x64(self):
        self._check(Brave('nightly', 'x64', is_system_level=False), [
            'BraveBrowserStandaloneNightlySetup.exe'
        ])
    def test_release_x86_system(self):
        self._check(Brave('release', 'x86', is_system_level=True), [
            'BraveBrowserStandaloneSetup32.exe'
        ])
    def test_origin_beta_arm64(self):
        self._check(Origin('beta', 'arm64', is_system_level=False), [
            'BraveOriginStandaloneBetaSetupArm64.exe'
        ])
    def _check(self, browser, expected):
        candidates = expected + [
            'BraveBrowserNightlySetup.exe',
            'BraveBrowserStandaloneNightlySetup.exe.sha256',
            'BraveBrowserSilentNightlySetup.exe',
            'BraveBrowserUntaggedNightlySetup.exe',
            'BraveBrowserNightlySetup32.exe',
            'BraveBrowserSetup.exe',
            'BraveOriginNightlySetup.exe',
            'brave-v1.97.17-win32-x64.zip',
        ]
        accepted = [n for n in candidates if browser.accepts_installer(n)]
        self.assertEqual(expected, accepted)
