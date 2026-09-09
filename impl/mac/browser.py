from impl.actions import Install
from impl.browser import Browser
from impl.sudo import sudo
from os import getpid, listdir
from os.path import exists, join, expanduser, basename
from plistlib import load
from shutil import rmtree, copytree
from subprocess import run, DEVNULL
from time import time


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
        sudo(_run, 'installer', '-pkg', path, '-target', '/')


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
        return exists(self.dir)

    @property
    def version(self):
        info_plist_path = join(self.dir, 'Contents', 'Info.plist')
        try:
            with open(info_plist_path, 'rb') as f:
                plist = load(f)
        except FileNotFoundError:
            return None
        return plist['CFBundleShortVersionString'].split('.', 1)[1]

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
            sudo(rmtree, self.dir)

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


def _get_extension(file_name):
    return file_name.rsplit('.', 1)[-1]


def _run(*args):
    run(args, check=True, stdout=DEVNULL, stderr=DEVNULL)
