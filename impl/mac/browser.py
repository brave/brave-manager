from impl.actions import Install
from impl.browser import Browser
from impl.elevate import elevate
from os import getpid, listdir, stat
from os.path import exists, join, expanduser, basename
from plistlib import load
from shutil import rmtree, copytree
from subprocess import run, DEVNULL
from time import time

import os


class InstallDmg(Install):
    def _run_installer(self, path):
        mount_point = f'/Volumes/temp_{getpid()}_{int(time())}'
        _run('hdiutil', 'attach', path, '-nobrowse', '-mountpoint', mount_point)
        try:
            app_name = \
                [f for f in listdir(mount_point) if f.endswith('.app')][0]
            src_path = join(mount_point, app_name)
            dst_path = join('/Applications', app_name)
            copytree(src_path, dst_path, symlinks=True)
        finally:
            _run('hdiutil', 'detach', mount_point)


class InstallPkg(Install):
    def _run_installer(self, path):
        elevate(_run, 'installer', '-pkg', path, '-target', '/')


class MacBrowser(Browser):

    INSTALL_ACTIONS = {
        'user': {'dmg': InstallDmg},
        'system': {'pkg': InstallPkg}
    }
    SUPPORTED_ARCHITECTURES = ('x64', 'arm64', 'universal')

    brand = None
    bundle_id_suffix = None

    @property
    def dir(self):
        return join('/Applications', f'{self._bundle_name}.app')

    @property
    def is_installed(self):
        if not exists(self.dir):
            return False
        is_owned_by_user = stat(self.dir).st_uid == os.getuid()
        if (self.scope == 'user') != is_owned_by_user:
            return False
        executable_name = self._info_plist['CFBundleExecutable']
        executable = join(self.dir, 'Contents', 'MacOS', executable_name)
        return _get_architecture(executable) == self.architecture

    @property
    def version(self):
        try:
            info_plist = self._info_plist
        except FileNotFoundError:
            return None
        return info_plist['CFBundleShortVersionString'].split('.', 1)[1]

    @property
    def _info_plist(self):
        with open(join(self.dir, 'Contents', 'Info.plist'), 'rb') as f:
            return load(f)

    @property
    def profile_paths(self):
        d = self._bundle_name_dashed
        s = self.bundle_id_suffix + \
            ('' if self.channel == 'release' else f'.{self.channel}')
        return [expanduser(f'~/Library/{p}') for p in (
            f'Application Support/BraveSoftware/{d}',
            f'Caches/BraveSoftware/{d}',
            f'Saved Application State/com.brave.Browser{s}.savedState',
            f'Caches/com.brave.Browser{s}',
            f'Preferences/com.brave.Browser{s}.plist',
        )]

    def uninstall(self):
        try:
            rmtree(self.dir)
        except PermissionError:
            elevate(rmtree, self.dir)

    def launch(self):
        run(['open', '-a', self.dir])

    def accepts_installer(self, name):
        return name in {
            f'{self._bundle_name_dashed}-{self.architecture}.{extension}'
            for extension in self.INSTALL_ACTIONS[self.scope]
        }

    def create_install_action(self, version, installer_url):
        extension = _get_extension(basename(installer_url))
        install_action = self.INSTALL_ACTIONS[self.scope][extension]
        return install_action(version, installer_url)

    @property
    def _bundle_name(self):
        if self.channel == 'release':
            return self.brand
        return f'{self.brand} {self.channel.title()}'

    @property
    def _bundle_name_dashed(self):
        return self._bundle_name.replace(' ', '-')


class Brave(MacBrowser):
    brand = 'Brave Browser'
    product_title = 'Brave'
    channels = ('nightly', 'beta', 'release')
    bundle_id_suffix = ''


class Origin(MacBrowser):
    brand = 'Brave Origin'
    product_title = 'Origin'
    channels = ('nightly', 'beta')
    bundle_id_suffix = '.origin'


def _get_architecture(executable_path):
    with open(executable_path, 'rb') as f:
        header = f.read(8)
    magic = header[:4]
    if magic == b'\xca\xfe\xba\xbe':
        # Fat binary
        return 'universal'
    if magic == b'\xcf\xfa\xed\xfe':
        # 64-bit Mach-O, little endian
        cpu_type = int.from_bytes(header[4:8], 'little')
        return {0x01000007: 'x64', 0x0100000c: 'arm64'}[cpu_type]
    raise ValueError(f'Unknown executable format: {executable_path}')


def _get_extension(file_name):
    return file_name.rsplit('.', 1)[-1]


def _run(*args):
    run(args, check=True, stdout=DEVNULL, stderr=DEVNULL)
