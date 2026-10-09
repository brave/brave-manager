from glob import glob
from impl.app import App
from impl.elevate import elevate
from impl.win import registry
from impl.win.browser import UPDATE_LOG_PATH
from os import listdir, remove
from os.path import dirname, exists, join
from shutil import rmtree
from subprocess import run
from tempfile import gettempdir
from time import monotonic, sleep
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
        # When Omaha 4 takes over, it writes its own version to Omaha 3's
        # registry key and leaves a copy of itself at Omaha 3's path. So
        # neither the key nor the file prove that Omaha 3 is installed. Only an
        # Omaha 3 version does. Omaha 4's versions follow the browser's.
        version = self.version
        return version is not None and version.startswith('1.3.')

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
        if self.is_system_level:
            elevate(_uninstall_omaha4, True)
        else:
            _uninstall_omaha4(False)

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
    _delete_omaha3_temp_files(is_system_level)


def _uninstall_omaha4(is_system_level):
    omaha4 = Omaha4(is_system_level)
    exe = join(omaha4.dir, omaha4.version, 'updater.exe')
    # The uninstaller deletes the installation directory asynchronously after
    # it exits. An interrupted or failed earlier uninstall can leave the
    # directory without the executable.
    if exists(exe):
        command = [exe, '--uninstall']
        if is_system_level:
            command.append('--system')
        run(command, check=True)
    _delete_dir(omaha4.dir)
    _delete_omaha4_takeover_remnants(is_system_level)


def _delete_dir(path, timeout_seconds=30):
    # The uninstaller's crash handler keeps updater.exe locked for a moment
    # after the uninstaller has exited. So we retry.
    deadline = monotonic() + timeout_seconds
    while exists(path):
        try:
            rmtree(path)
        except OSError:
            if monotonic() >= deadline:
                raise
            sleep(.5)


def _delete_omaha4_takeover_remnants(is_system_level):
    # Omaha 4's takeover writes its version into Omaha 3's registry key and puts
    # a copy of itself at BraveUpdate.exe. Its uninstaller does not clean these
    # up. Omaha 3's installer would then refuse to install itself.
    omaha3 = Omaha3(is_system_level)
    root, key = omaha3.registry_key
    for name in ('version', 'UninstallCmdLine', 'path'):
        registry.delete_value(root, key, name)
    for subkey in ('Clients', 'ClientState'):
        registry.delete_key(root, rf'{key}\{subkey}\{OMAHA3_GUID}')
    rmtree(dirname(omaha3.exe), ignore_errors=True)


def _delete_omaha3_temp_files(is_system_level):
    # Omaha 3 leaves GUT*.tmp files and GUM*.tmp directories behind. When Brave
    # is installed and uninstalled many times, they can take up a lot of space.
    if is_system_level:
        temp_dir = join(os.environ['SYSTEMROOT'], 'SystemTemp')
    else:
        temp_dir = gettempdir()
    for path in glob(join(temp_dir, 'GUT*.tmp')):
        try:
            remove(path)
        except OSError:
            # Maybe it's in use, or it is a directory.
            pass
    for path in glob(join(temp_dir, 'GUM*.tmp')):
        try:
            rmtree(path)
        except OSError:
            # Maybe it's in use, or it is a file.
            pass
