from impl.actions import InstallDmg, InstallPkg
from impl.app import App
from impl.sudo import sudo
from os.path import exists, join, expanduser, basename
from plistlib import load
from shutil import rmtree
from subprocess import run


class MacApp(App):

    INSTALL_ACTIONS = {'dmg': InstallDmg, 'pkg': InstallPkg}

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
        return (
            name.startswith(self._bundle_name_dashed)
            and _get_extension(name) in self.INSTALL_ACTIONS
        )

    def create_install_action(self, version, installer_url):
        extension = _get_extension(basename(installer_url))
        return self.INSTALL_ACTIONS[extension](version, installer_url)

    @property
    def _bundle_name(self):
        if self.channel == 'release':
            return self.brand
        return f'{self.brand} {self.channel.title()}'

    @property
    def _bundle_name_dashed(self):
        return self._bundle_name.replace(' ', '-')


def _get_extension(file_name):
    return file_name.rsplit('.', 1)[-1]
