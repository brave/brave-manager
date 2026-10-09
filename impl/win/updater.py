from glob import glob
from impl.app import App
from impl.elevate import elevate
from impl.win import registry, task_scheduler
from impl.win.browser import UPDATE_LOG_PATH
from os import listdir, remove
from os.path import dirname, exists, join
from shutil import rmtree
from subprocess import run
from tempfile import gettempdir
from time import monotonic, sleep
from winreg import HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE

import os
import win32con
import win32service

OMAHA3_GUID = '{B131C935-9BE6-41DA-9599-1F776BEB8019}'

# Per-user installations start at logon via values in this key:
RUN_KEY = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
OMAHA3_RUN_VALUE = 'BraveSoftware Update'
# Followed by the version:
OMAHA4_RUN_VALUE_PREFIX = 'BraveUpdaterTaskUser'

# System-wide installations register services:
SERVICES_KEY = r'SYSTEM\CurrentControlSet\Services'
# Optionally followed by a timestamp:
OMAHA3_SERVICE_PREFIX = 'brave'
# Followed by the version:
OMAHA4_SERVICE_PREFIXES = ('BraveUpdaterService', 'BraveUpdaterInternalService')

# 64-bit and 32-bit COM registrations live in separate views:
CLASSES_KEYS = (r'SOFTWARE\Classes', r'SOFTWARE\Classes\WOW6432Node')


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
        is_system_level = self.is_system_level
        return bool(
            _find_run_values(is_system_level, OMAHA3_RUN_VALUE)
            or _find_omaha3_tasks(is_system_level)
            or _find_services(is_system_level, _is_omaha3_service)
            or _has_shared_remnants(is_system_level)
        )

    def delete_remnants(self):
        if self.is_system_level:
            elevate(_delete_omaha3_remnants, True)
        else:
            _delete_omaha3_remnants(False)

    @property
    def task_prefix(self):
        # The tasks are in the root folder. Per-user tasks' names continue
        # with the user's SID.
        if self.is_system_level:
            return 'BraveSoftwareUpdateTaskMachine'
        return 'BraveSoftwareUpdateTaskUser'

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
        is_system_level = self.is_system_level
        return bool(
            exists(self.dir)
            or _find_run_values(is_system_level, OMAHA4_RUN_VALUE_PREFIX)
            or any(_find_omaha4_tasks(is_system_level))
            or _find_services(is_system_level, _is_omaha4_service)
            or _find_omaha4_com_registrations(is_system_level)
            or _has_shared_remnants(is_system_level)
        )

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

    @property
    def task_folder(self):
        # The tasks are in its BraveUpdater subfolder:
        if self.is_system_level:
            return r'\BraveSoftwareSystem'
        return r'\BraveSoftwareUser'


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
    _delete_tasks(_find_omaha3_tasks(is_system_level))
    _delete_services(_find_services(is_system_level, _is_omaha3_service))
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
    _delete_tasks(*_find_omaha4_tasks(is_system_level))
    _delete_services(_find_services(is_system_level, _is_omaha4_service))
    _delete_omaha4_com_registrations(is_system_level)
    _delete_shared_remnants(is_system_level)


def _find_services(is_system_level, is_match):
    if not is_system_level:
        return []
    result = []
    for name in registry.list_subkeys(HKEY_LOCAL_MACHINE, SERVICES_KEY):
        key = rf'{SERVICES_KEY}\{name}'
        display_name, image_path = (
            _read_string(HKEY_LOCAL_MACHINE, key, value_name)
            for value_name in ('DisplayName', 'ImagePath')
        )
        if is_match(name, display_name, image_path):
            result.append(name)
    return result


def _is_omaha3_service(name, display_name, image_path):
    # This is how Omaha 4 recognizes Omaha 3's services when it takes over. Its
    # integration tests create such services with an unrelated image path.
    # But Omaha 3 takes the display name from its localized resources. So we
    # also check the path:
    return (
        name.startswith(OMAHA3_SERVICE_PREFIX)
        and display_name.startswith('Brave Update Service')
    ) or _is_in_dir(image_path, dirname(Omaha3(True).exe))


def _is_omaha4_service(name, display_name, image_path):
    return _is_in_dir(image_path, Omaha4(True).dir)


def _is_in_dir(command_line, dir_path):
    # The executable path in a command line can be quoted:
    return command_line.lstrip('"').lower().startswith(dir_path.lower() + '\\')


def _delete_services(names):
    scm = win32service.OpenSCManager(
        None, None, win32service.SC_MANAGER_CONNECT
    )
    try:
        for name in names:
            service = win32service.OpenService(scm, name, win32con.DELETE)
            try:
                win32service.DeleteService(service)
            finally:
                win32service.CloseServiceHandle(service)
    finally:
        win32service.CloseServiceHandle(scm)


def _read_string(root, key, name):
    try:
        return str(registry.read_value(root, key, name))
    except FileNotFoundError:
        return ''


def _find_omaha3_tasks(is_system_level):
    prefix = Omaha3(is_system_level).task_prefix.lower()
    tasks, _ = task_scheduler.list_folder('\\')
    return [
        path for path, is_current_user in tasks
        if path[1:].lower().startswith(prefix)
        # An elevated process also sees other users' tasks:
        and (is_system_level or is_current_user)
    ]


def _find_omaha4_tasks(is_system_level):
    folder = Omaha4(is_system_level).task_folder
    return _find_tasks_recursively(folder, is_system_level)


def _find_tasks_recursively(folder, is_system_level):
    """
    Returns the tasks of the given scope in the folder and its subfolders, and
    the folders that are empty once those tasks are deleted. Subfolders come
    before their parents.
    """
    listing = task_scheduler.list_folder(folder)
    if listing is None:
        return [], []
    tasks, subfolders = listing
    result_tasks, result_folders = [], []
    for subfolder in subfolders:
        sub_tasks, sub_folders = \
            _find_tasks_recursively(subfolder, is_system_level)
        result_tasks += sub_tasks
        result_folders += sub_folders
    # All users' per-user installations share the folder. An elevated process
    # also sees the other users' tasks:
    own_tasks = [
        path for path, is_current_user in tasks
        if is_system_level or is_current_user
    ]
    result_tasks += own_tasks
    if len(own_tasks) == len(tasks) and set(subfolders) <= set(result_folders):
        result_folders.append(folder)
    return result_tasks, result_folders


def _delete_tasks(tasks, folders=()):
    for path in tasks:
        task_scheduler.delete_task(path)
    for path in folders:
        task_scheduler.delete_folder(path)


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


def _delete_omaha4_com_registrations(is_system_level):
    for root, key in _find_omaha4_com_registrations(is_system_level):
        registry.delete_key(root, key)


def _find_omaha4_com_registrations(is_system_level):
    # Omaha 4's classes, and the type libraries of its interfaces, point into
    # its installation directory. Its service hosts the classes of system-wide
    # installations:
    root = HKEY_LOCAL_MACHINE if is_system_level else HKEY_CURRENT_USER
    dir_path = Omaha4(is_system_level).dir
    keys = []
    for classes_key in CLASSES_KEYS:
        keys += _find_com_registrations(root, classes_key, dir_path)
        keys += _find_com_service_registrations(
            root, classes_key, OMAHA4_SERVICE_PREFIXES
        )
    return [(root, key) for key in keys]


def _delete_omaha3_com_registrations(is_system_level):
    for root, key in _find_omaha3_com_registrations(is_system_level):
        registry.delete_key(root, key)


def _find_omaha3_com_registrations(is_system_level):
    # Omaha 3's classes, and the interfaces they proxy, point into its
    # installation directory. Its services host some of the classes of
    # system-wide installations:
    root = HKEY_LOCAL_MACHINE if is_system_level else HKEY_CURRENT_USER
    dir_path = dirname(Omaha3(is_system_level).exe)
    keys = []
    for classes_key in CLASSES_KEYS:
        keys += _find_com_registrations(root, classes_key, dir_path)
        keys += _find_com_service_registrations(
            root, classes_key, (OMAHA3_SERVICE_PREFIX,)
        )
    # Omaha 3's ProgIDs point to classes, not into the directory. Some of those
    # classes were taken over by Omaha 4, whose uninstaller deleted them. So we
    # recognize the ProgIDs by name. They are not split by view:
    keys += _find_progids(root, r'SOFTWARE\Classes', 'BraveSoftwareUpdate.')
    return [(root, key) for key in keys]


def _find_com_registrations(root, classes_key, dir_path):
    """
    Returns the keys of the classes whose server lies in dir_path, of the type
    libraries in dir_path, and of the interfaces that use one of them.
    """
    clsids = set()
    for clsid in _list_subkeys_if_exists(root, rf'{classes_key}\CLSID'):
        for server in ('InprocServer32', 'InprocHandler32', 'LocalServer32'):
            server_key = rf'{classes_key}\CLSID\{clsid}\{server}'
            if _is_in_dir(_read_string(root, server_key, ''), dir_path):
                clsids.add(clsid.upper())
    libids = set()
    for libid in _list_subkeys_if_exists(root, rf'{classes_key}\TypeLib'):
        typelib_key = rf'{classes_key}\TypeLib\{libid}'
        if _is_type_library_in_dir(root, typelib_key, dir_path):
            libids.add(libid.upper())
    result = []
    for iid in _list_subkeys_if_exists(root, rf'{classes_key}\Interface'):
        interface_key = rf'{classes_key}\Interface\{iid}'
        proxy_stub = \
            _read_string(root, rf'{interface_key}\ProxyStubClsid32', '')
        typelib = _read_string(root, rf'{interface_key}\TypeLib', '')
        if proxy_stub.upper() in clsids or typelib.upper() in libids:
            result.append(interface_key)
    for clsid in clsids:
        result.append(rf'{classes_key}\CLSID\{clsid}')
    for libid in libids:
        result.append(rf'{classes_key}\TypeLib\{libid}')
    return result


def _find_com_service_registrations(root, classes_key, service_prefixes):
    """
    Returns the keys of the AppIDs whose LocalService starts with one of the
    given prefixes, and of the classes and AppID entries that refer to them.
    """
    appids_key = rf'{classes_key}\AppID'
    names = _list_subkeys_if_exists(root, appids_key)
    appids = set()
    for name in names:
        service = _read_string(root, rf'{appids_key}\{name}', 'LocalService')
        if service.startswith(service_prefixes):
            appids.add(name.upper())
    if not appids:
        return []
    result = []
    for name in names:
        appid_key = rf'{appids_key}\{name}'
        # Eg. an entry for the server's executable name:
        refers_to = _read_string(root, appid_key, 'AppID').upper()
        if name.upper() in appids or refers_to in appids:
            result.append(appid_key)
    for clsid in _list_subkeys_if_exists(root, rf'{classes_key}\CLSID'):
        clsid_key = rf'{classes_key}\CLSID\{clsid}'
        if _read_string(root, clsid_key, 'AppID').upper() in appids:
            result.append(clsid_key)
    return result


def _is_type_library_in_dir(root, key, dir_path):
    # The paths are at <version>\<LCID>\<platform>, eg. 1.0\0\win64:
    for version in _list_subkeys_if_exists(root, key):
        version_key = rf'{key}\{version}'
        for lcid in _list_subkeys_if_exists(root, version_key):
            lcid_key = rf'{version_key}\{lcid}'
            for platform in _list_subkeys_if_exists(root, lcid_key):
                path = _read_string(root, rf'{lcid_key}\{platform}', '')
                if _is_in_dir(path, dir_path):
                    return True
    return False


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
