from argparse import ArgumentParser
from os.path import join, exists
from shutil import rmtree
from subprocess import run
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

ALL_CHANNELS = list(BRAVE_APP_NAMES)

class UninstallNeedsAdminError(Exception):
    def __str__(self):
        return f'Cannot uninstall {self.args[0]}. Please re-run as admin.'

def main():
    channels, user_or_machine, delete_profiles = parse_args()
    for is_user in user_or_machine:
        user_or_machine_desc = 'user' if is_user else 'machine'
        for channel in channels:
            try:
                was_installed = uninstall_brave(is_user, channel)
            except UninstallNeedsAdminError as e:
                print(e)
            else:
                if was_installed:
                    app_name = BRAVE_APP_NAMES[channel]
                    print(f'Uninstalled {app_name} ({user_or_machine_desc}).')
        try:
            was_installed = uninstall_brave_update(is_user)
        except UninstallNeedsAdminError as e:
            print(e)
        else:
            if was_installed:
                print(f'Uninstalled Brave Update ({user_or_machine_desc}).')
    if delete_profiles:
        for channel in channels:
            if delete_user_data_dir(channel):
                app_name = BRAVE_APP_NAMES[channel]
                print(f'Deleted user data directory for {app_name}.')

def uninstall_brave(is_user, channel):
    was_installed = False
    hklm_hkcu = get_hklm_hkcu(is_user)
    app_name = BRAVE_APP_NAMES[channel]
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
        app_guid = BRAVE_APP_IDS[channel]
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

def delete_user_data_dir(channel):
    app_name = BRAVE_APP_NAMES[channel]
    user_data_dir = \
        join(os.getenv('LOCALAPPDATA'), 'BraveSoftware', app_name, 'User Data')
    try:
        rmtree(user_data_dir)
    except FileNotFoundError:
        return False
    return True

def check_admin(is_user, app_name):
    if not is_user and not is_user_an_admin():
        raise UninstallNeedsAdminError(app_name)

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
        '--channel', choices=['all'] + ALL_CHANNELS, default='all'
    )
    parser.add_argument(
        '--user_or_machine', choices=['both', 'user', 'machine'], default='both'
    )
    parser.add_argument('--delete_profiles', action='store_true')
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

    return channels, uninstall_user_or_machine, args.delete_profiles

if __name__ == '__main__':
    main()
