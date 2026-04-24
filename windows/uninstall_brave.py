from argparse import ArgumentParser
from glob import glob
from os import remove
from os.path import join, exists
from shutil import rmtree
from subprocess import run
from tempfile import gettempdir
from winreg import OpenKey, HKEY_LOCAL_MACHINE, HKEY_CURRENT_USER, \
    QueryValueEx, EnumKey, DeleteKey, QueryInfoKey

import ctypes
import os
import sys

WINDOWS_UNINSTALL_KEY = \
    r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'

UPDATE_KEY = r'SOFTWARE\WOW6432Node\BraveSoftware\Update'

BRAVE_APP_NAMES = {
    'nightly': 'Brave-Browser-Nightly',
    'dev': 'Brave-Browser-Dev',
    'development': 'Brave-Browser-Development',
    'beta': 'Brave-Browser-Beta',
    'release': 'Brave-Browser'
}

BRAVE_APP_IDS = {
    'nightly': '{C6CB981E-DB30-4876-8639-109F8933582C}',
    'dev': '{CB2150F2-595F-4633-891A-E39720CE0531}',
    'beta': '{103BD053-949B-43A8-9120-2E424887DE11}',
    'release': '{AFE6A462-C574-4B8A-AF43-4CC60DF4563B}'
}

ORIGIN_APP_IDS = {
    'nightly': '{50474E96-9CD2-4BC8-B0A7-0D4B6EF2E709}',
    'dev': '{716D6A4A-D071-47A8-AC64-DBDE3EE3797B}',
    'beta': '{56DA94FD-D872-416B-BFC4-1D7011DA7473}',
    'release': '{F1EF32DE-F987-4289-81D2-6C4780027F9B}'
}

ALL_CHANNELS = list(BRAVE_APP_NAMES)

class UninstallNeedsAdminError(Exception):
    def __str__(self):
        return f'Cannot uninstall {self.args[0]}. Please re-run as admin.'

def main():
    is_origin_values, channels, user_or_machine, delete_profiles, \
        should_delete_temp_files = parse_args()
    for channel in channels:
        for is_origin in is_origin_values:
            app_name = get_app_name(is_origin, channel)
            for is_user in user_or_machine:
                try:
                    was_installed = uninstall_brave(is_origin, is_user, channel)
                except UninstallNeedsAdminError as e:
                    print(e)
                    continue
                if was_installed:
                    user_or_machine_desc = 'user' if is_user else 'machine'
                    print(f'Uninstalled {app_name} ({user_or_machine_desc}).')
            if delete_profiles and delete_user_data_dir(is_origin, channel):
                print(f'Deleted user data directory for {app_name}.')
    for is_user in user_or_machine:
        try:
            was_installed = uninstall_brave_update(is_user)
        except UninstallNeedsAdminError as e:
            print(e)
        else:
            if was_installed:
                user_or_machine_desc = 'user' if is_user else 'machine'
                print(f'Uninstalled Brave Update ({user_or_machine_desc}).')
        if should_delete_temp_files:
            delete_temp_files(is_user)

def uninstall_brave(is_origin, is_user, channel):
    was_installed = False
    hklm_hkcu = get_hklm_hkcu(is_user)
    app_name = get_app_name(is_origin, channel)
    uninstall_key = get_brave_key(
        is_user, WINDOWS_UNINSTALL_KEY + '\\BraveSoftware ' + app_name
    )
    try:
        key = OpenKey(hklm_hkcu, uninstall_key)
    except FileNotFoundError:
        uninstall_key_exists = False
    else:
        was_installed = uninstall_key_exists = True
        with key:
            check_admin(is_user, app_name)
            try:
                uninstall_string = QueryValueEx(key, 'UninstallString')[0]
            except FileNotFoundError:
                pass
            else:
                try:
                    cp = run(uninstall_string + ' --force-uninstall')
                except FileNotFoundError:
                    pass
                else:
                    if cp.returncode not in (0, 19):
                        # Raise an error.
                        cp.check_returncode()
    if uninstall_key_exists:
        delete_key_recursive(hklm_hkcu, uninstall_key)
    install_dir = get_brave_file(is_user, app_name, 'Application')
    if exists(install_dir):
        was_installed = True
        check_admin(is_user, app_name)
        rmtree(install_dir)
    try:
        app_guid = get_app_id(is_origin, channel)
    except KeyError:
        # This happens for channel 'development', which does not have updates.
        pass
    else:
        update_key = get_brave_update_clients_key(is_user, app_guid)
        if key_exists(hklm_hkcu, update_key):
            was_installed = True
            check_admin(is_user, app_name)
            delete_key_recursive(hklm_hkcu, update_key)
    return was_installed

def uninstall_brave_update(is_user):
    hklm_hkcu = get_hklm_hkcu(is_user)
    clients_key = get_brave_update_clients_key(is_user)
    try:
        with OpenKey(hklm_hkcu, clients_key) as key:
            num_apps = QueryInfoKey(key)[0]
    except FileNotFoundError:
        num_apps = 0
    if num_apps == 1: # Only the updater is installed; It will uninstall itself.
        brave_update_exe = get_brave_update_exe(is_user)
        assert exists(brave_update_exe)
        check_admin(is_user, 'Brave Update')
        run([brave_update_exe, '/uninstall'], check=True)
        return True
    return False

def delete_user_data_dir(is_origin, channel):
    app_name = get_app_name(is_origin, channel)
    user_data_dir = \
        join(os.getenv('LOCALAPPDATA'), 'BraveSoftware', app_name, 'User Data')
    try:
        rmtree(user_data_dir)
    except FileNotFoundError:
        return False
    return True

def delete_temp_files(is_user):
    # Omaha creates temporary files with pattern GUT*.tmp and temporary dirs
    # with pattern GUM*.tmp. When Brave is uninstalled and re-installed many
    # times, then these can take up infinite space.
    temp_dir = get_temp_dir(is_user)
    for file_path in glob(join(temp_dir, 'GUT*.tmp')):
        try:
            remove(file_path)
        except OSError:
            # Maybe it's in use, or it is a directory.
            pass
    for dir_path in glob(join(temp_dir, 'GUM*.tmp')):
        try:
            rmtree(dir_path)
        except OSError:
            # Maybe it's in use, or it is a file.
            pass

def check_admin(is_user, app_name):
    if not is_user and not is_user_an_admin():
        raise UninstallNeedsAdminError(app_name)

def get_app_name(is_origin, channel):
    result = BRAVE_APP_NAMES[channel]
    return result.replace('Browser', 'Origin') if is_origin else result

def get_app_id(is_origin, channel):
    return (ORIGIN_APP_IDS if is_origin else BRAVE_APP_IDS)[channel]

def get_temp_dir(is_user):
    return gettempdir() if is_user else r'C:\Windows\SystemTemp'

def get_brave_key(is_user, template):
    return template.replace('WOW6432Node\\', '') if is_user else template

def get_brave_update_clients_key(is_user, app_guid=None):
    update_key_root = get_brave_key(is_user, UPDATE_KEY)
    result = join(update_key_root, 'Clients')
    if app_guid is not None:
        result = join(result, app_guid)
    return result

def get_brave_file(is_user, *relative_path):
    pardir = os.getenv('LOCALAPPDATA' if is_user else 'PROGRAMFILES(X86)')
    return join(pardir, 'BraveSoftware', *relative_path)

def get_brave_update_exe(is_user):
    return get_brave_file(is_user, 'Update', 'BraveUpdate.exe')

def get_hklm_hkcu(is_user):
    return HKEY_CURRENT_USER if is_user else HKEY_LOCAL_MACHINE

def is_user_an_admin():
    return ctypes.windll.shell32.IsUserAnAdmin() != 0

def key_exists(parent_key, child_name):
    try:
        with OpenKey(parent_key, child_name):
            return True
    except FileNotFoundError:
        return False

def delete_key_recursive(parent_key, child_name):
    try:
        key = OpenKey(parent_key, child_name)
    except FileNotFoundError:
        return
    with key as child:
        # Delete child keys until we run out:
        while True:
            try:
                grandchild = EnumKey(child, 0)
            except OSError:
                break
            else:
                delete_key_recursive(child, grandchild)
        DeleteKey(parent_key, child_name)

def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        '--flavor', choices=['both', 'browser', 'origin'], default='both'
    )
    parser.add_argument(
        '--channel', choices=['all'] + ALL_CHANNELS, default='all'
    )
    parser.add_argument(
        '--user_or_machine', choices=['both', 'user', 'machine'], default='both'
    )
    parser.add_argument('--delete_profiles', action='store_true')
    parser.add_argument('--delete_temp_files', action='store_true')
    args = parser.parse_args()

    if args.channel == 'all':
        channels = ALL_CHANNELS
    else:
        channels = [args.channel]

    uninstall_user_or_machine = []

    if args.user_or_machine in {'both', 'user'}:
        uninstall_user_or_machine.append(True)

    if args.user_or_machine in {'both', 'machine'}:
        uninstall_user_or_machine.append(False)

    is_origin_values = []

    if args.flavor in {'both', 'browser'}:
        is_origin_values.append(False)

    if args.flavor in {'both', 'origin'}:
        is_origin_values.append(True)

    return is_origin_values, channels, uninstall_user_or_machine, \
        args.delete_profiles, args.delete_temp_files

if __name__ == '__main__':
    main()
