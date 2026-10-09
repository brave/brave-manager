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

# Per-user installations start at logon via values in this key:
RUN_KEY = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
OMAHA3_RUN_VALUE = 'BraveSoftware Update'
# Followed by the version:
OMAHA4_RUN_VALUE_PREFIX = 'BraveUpdaterTaskUser'


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
    def has_remnants(self):
        return bool(_find_run_values(self.is_system_level, OMAHA3_RUN_VALUE)) \
            or _has_shared_remnants(self.is_system_level)

    def delete_remnants(self):
        if self.is_system_level:
            elevate(_delete_omaha3_remnants, True)
        else:
            _delete_omaha3_remnants(False)

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
    def has_remnants(self):
        run_values = \
            _find_run_values(self.is_system_level, OMAHA4_RUN_VALUE_PREFIX)
        return exists(self.dir) or bool(run_values) \
            or _has_shared_remnants(self.is_system_level)

    def delete_remnants(self):
        if self.is_system_level:
            elevate(_delete_omaha4_remnants, True)
        else:
            _delete_omaha4_remnants(False)

    @property
    def dir(self):
        if self.is_system_level:
            parent_dir = os.environ['PROGRAMFILES(X86)']
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
    _delete_omaha3_remnants(is_system_level)


def _delete_omaha3_remnants(is_system_level):
    _delete_run_values(is_system_level, OMAHA3_RUN_VALUE)
    _delete_shared_remnants(is_system_level)


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
    _delete_omaha4_remnants(is_system_level)


def _delete_omaha4_remnants(is_system_level):
    _delete_dir(Omaha4(is_system_level).dir)
    _delete_run_values(is_system_level, OMAHA4_RUN_VALUE_PREFIX)
    _delete_shared_remnants(is_system_level)


def _find_run_values(is_system_level, prefix):
    if is_system_level:
        return []
    names = registry.list_values(HKEY_CURRENT_USER, RUN_KEY)
    return [name for name in names if name.lower().startswith(prefix.lower())]


def _delete_run_values(is_system_level, prefix):
    for name in _find_run_values(is_system_level, prefix):
        registry.delete_value(HKEY_CURRENT_USER, RUN_KEY, name)


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


def _has_shared_remnants(is_system_level):
    if _is_any_updater_installed(is_system_level):
        return False
    omaha3 = Omaha3(is_system_level)
    return exists(dirname(omaha3.exe)) \
        or any(
            registry.key_exists(root, key)
            for root, key in _get_shared_registry_keys(is_system_level)
        ) \
        or bool(_find_omaha3_com_registrations(is_system_level))


def _delete_shared_remnants(is_system_level):
    # Omaha 4's takeover writes its version into Omaha 3's registry key and puts
    # a copy of itself at BraveUpdate.exe. So the two updaters share Omaha 3's
    # key and installation directory. Neither updater's uninstaller deletes the
    # key completely. If Omaha 4's version remains in it, Omaha 3's installer
    # refuses to install itself. So we delete the key, together with the
    # directory, once neither updater is installed anymore:
    if _is_any_updater_installed(is_system_level):
        return
    for root, key in _get_shared_registry_keys(is_system_level):
        registry.delete_key(root, key)
    rmtree(dirname(Omaha3(is_system_level).exe), ignore_errors=True)
    # Omaha 3's uninstaller deletes its COM registrations. But Omaha 4's
    # takeover removes Omaha 3 without running that uninstaller. The
    # registrations then remain, pointing into the directory we just deleted.
    _delete_omaha3_com_registrations(is_system_level)


def _get_shared_registry_keys(is_system_level):
    root, key = Omaha3(is_system_level).registry_key
    result = [(root, key)]
    # Omaha 4's takeover also imports apps registered in the 64-bit view of
    # HKLM. Its integration tests create such registrations. HKCU\SOFTWARE is
    # not split by view.
    if is_system_level:
        result.append((root, r'SOFTWARE\BraveSoftware\Update'))
    return result


def _is_any_updater_installed(is_system_level):
    return any(updater(is_system_level).is_installed for updater in UPDATERS)


def _delete_omaha3_com_registrations(is_system_level):
    for root, key in _find_omaha3_com_registrations(is_system_level):
        registry.delete_key(root, key)


def _find_omaha3_com_registrations(is_system_level):
    # Omaha 3's classes, and the interfaces they proxy, point into its
    # installation directory. 64-bit and 32-bit registrations live in separate
    # views:
    root = HKEY_LOCAL_MACHINE if is_system_level else HKEY_CURRENT_USER
    dir_path = dirname(Omaha3(is_system_level).exe)
    keys = []
    for classes_key in (r'SOFTWARE\Classes', r'SOFTWARE\Classes\WOW6432Node'):
        keys += _find_com_registrations(root, classes_key, dir_path)
    # Omaha 3's ProgIDs point to classes, not into the directory. Some of those
    # classes were taken over by Omaha 4, whose uninstaller deleted them. So we
    # recognize the ProgIDs by name. They are not split by view:
    keys += _find_progids(root, r'SOFTWARE\Classes', 'BraveSoftwareUpdate.')
    return [(root, key) for key in keys]


def _find_com_registrations(root, classes_key, dir_path):
    """
    Returns the keys of the classes whose server lies in dir_path, and of the
    interfaces that use one of them as their proxy/stub.
    """
    prefix = dir_path.lower() + '\\'
    clsids = set()
    for clsid in _list_subkeys_if_exists(root, rf'{classes_key}\CLSID'):
        for server in ('InprocServer32', 'InprocHandler32', 'LocalServer32'):
            server_key = rf'{classes_key}\CLSID\{clsid}\{server}'
            try:
                path = registry.read_value(root, server_key, '')
            except FileNotFoundError:
                continue
            # LocalServer32 values can be quoted and contain arguments:
            if path.lstrip('"').lower().startswith(prefix):
                clsids.add(clsid.upper())
    result = []
    for iid in _list_subkeys_if_exists(root, rf'{classes_key}\Interface'):
        interface_key = rf'{classes_key}\Interface\{iid}'
        try:
            proxy_stub = registry.read_value(
                root, rf'{interface_key}\ProxyStubClsid32', ''
            )
        except FileNotFoundError:
            continue
        if proxy_stub.upper() in clsids:
            result.append(interface_key)
    for clsid in clsids:
        result.append(rf'{classes_key}\CLSID\{clsid}')
    return result


def _find_progids(root, classes_key, prefix):
    return [
        rf'{classes_key}\{name}'
        for name in _list_subkeys_if_exists(root, classes_key)
        if name.lower().startswith(prefix.lower())
    ]


def _list_subkeys_if_exists(root, key):
    try:
        return registry.list_subkeys(root, key)
    except FileNotFoundError:
        return []


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
