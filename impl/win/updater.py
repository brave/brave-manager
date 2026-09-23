from impl.app import App
from impl.elevate import elevate
from impl.win import registry
from impl.win.browser import UPDATE_LOG_PATH
from os import listdir
from os.path import join
from subprocess import run
from winreg import HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE

import os

OMAHA3_GUID = '{B131C935-9BE6-41DA-9599-1F776BEB8019}'


class Omaha3(App):
    """
    Installed alongside the browser and uninstalls itself when the last app
    registered with it is uninstalled. Omaha 4 registers itself with Omaha 3
    when it takes over, and browsers register themselves when installed.
    """

    product_title = 'Omaha 3'

    @property
    def is_installed(self):
        return self.version is not None

    @property
    def version(self):
        # The uninstaller can't delete its own executable and schedules it for
        # deletion on reboot. So we check the registry instead of the file.
        try:
            return registry.read_value(*self.registry_key, 'version')
        except FileNotFoundError:
            return None

    def uninstall(self):
        if self.is_system_level:
            elevate(_uninstall_omaha3, True)
        else:
            _uninstall_omaha3(False)
        if self.is_installed:
            raise RuntimeError(
                f'{self} refused to uninstall. See {UPDATE_LOG_PATH}.'
            )

    @property
    def exe(self):
        if self.is_system_level:
            parent_dir = os.environ['PROGRAMFILES(X86)']
        else:
            parent_dir = os.environ['LOCALAPPDATA']
        return join(parent_dir, 'BraveSoftware', 'Update', 'BraveUpdate.exe')

    @property
    def registry_key(self):
        if self.is_system_level:
            return HKEY_LOCAL_MACHINE, \
                r'SOFTWARE\WOW6432Node\BraveSoftware\Update'
        return HKEY_CURRENT_USER, r'SOFTWARE\BraveSoftware\Update'


class Omaha4(App):
    """
    Its --uninstall spawns a script that deletes the installation
    directory once the updater has exited.
    """

    product_title = 'Omaha 4'

    @property
    def is_installed(self):
        return self.version is not None

    @property
    def version(self):
        try:
            names = listdir(self.dir)
        except FileNotFoundError:
            return None
        versions = []
        for name in names:
            try:
                versions.append(tuple(int(part) for part in name.split('.')))
            except ValueError:
                pass
        if not versions:
            return None
        return '.'.join(map(str, max(versions)))

    def uninstall(self):
        command = [join(self.dir, self.version, 'updater.exe'), '--uninstall']
        if self.is_system_level:
            command.append('--system')
            elevate(run, command)
        else:
            run(command, check=True)

    @property
    def dir(self):
        if self.is_system_level:
            parent_dir = os.environ['PROGRAMDATA']
        else:
            parent_dir = os.environ['LOCALAPPDATA']
        return join(parent_dir, 'BraveSoftware', 'BraveUpdater')


UPDATERS = (Omaha3, Omaha4)


def _uninstall_omaha3(is_system_level):
    # Omaha 3 refuses to uninstall while apps are registered with it. We want
    # to uninstall it regardless. So we unregister all apps first:
    omaha3 = Omaha3(is_system_level)
    root, key = omaha3.registry_key
    for guid in registry.list_subkeys(root, rf'{key}\Clients'):
        if guid.upper() != OMAHA3_GUID:
            registry.delete_key(root, rf'{key}\Clients\{guid}')
    run([omaha3.exe, '/uninstall'])
