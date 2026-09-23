from impl.app import App
from impl.elevate import elevate
from os.path import exists, join, expanduser
from plistlib import load
from shutil import rmtree
from subprocess import run


class BraveUpdater(App):

    product_title = 'Brave Updater'

    @property
    def dir(self):
        result = '/Library/Application Support/BraveSoftware/BraveUpdater'
        return result if self.is_system_level else expanduser('~' + result)

    @property
    def is_installed(self):
        return exists(self.dir)

    @property
    def version(self):
        info_plist_path = \
            join(_get_app_bundle(self.dir), 'Contents', 'Info.plist')
        try:
            with open(info_plist_path, 'rb') as f:
                return load(f)['CFBundleShortVersionString']
        except FileNotFoundError:
            return None

    def uninstall(self):
        if self.is_system_level:
            elevate(_uninstall, self.dir, True)
        else:
            _uninstall(self.dir, False)


UPDATERS = (BraveUpdater,)


def _uninstall(updater_dir, is_system_level):
    executable = \
        join(_get_app_bundle(updater_dir), 'Contents', 'MacOS', 'BraveUpdater')
    if exists(executable):
        args = [executable, '--uninstall']
        if is_system_level:
            args.append('--system')
        run(args, check=True)
    rmtree(updater_dir)


def _get_app_bundle(updater_dir):
    return join(updater_dir, 'Current', 'BraveUpdater.app')
