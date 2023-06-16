from argparse import ArgumentParser
from os.path import join, exists
from winreg import OpenKey, HKEY_LOCAL_MACHINE, HKEY_CURRENT_USER, QueryValueEx
from subprocess import run

import ctypes
import os
import sys

WINDOWS_UNINSTALL_KEY = \
    r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'

BRAVE_UNINSTALL_SUBKEYS = {
    'nightly': 'BraveSoftware Brave-Browser-Nightly',
    'dev': 'BraveSoftware Brave-Browser-Dev',
    'development': 'BraveSoftware Brave-Browser-Development',
    'beta': 'BraveSoftware Brave-Browser-Beta',
    'release': 'BraveSoftware Brave-Browser'
}

ALL_CHANNELS = list(BRAVE_UNINSTALL_SUBKEYS)

def main():
    channels, uninstall_user_or_machine = parse_args()
    for is_user in uninstall_user_or_machine:
        user_or_machine_desc = 'user' if is_user else 'machine'
        for channel in channels:
            brave_description = 'Brave %s (%s)' % (
                channel.title(), user_or_machine_desc
            )
            if is_brave_installed(is_user, channel):
                uninstall_brave(is_user, channel)
                print('Uninstalled %s.' % brave_description)
            else:            
                print(brave_description + ' is not installed.')
        if not any (is_brave_installed(is_user, ch) for ch in ALL_CHANNELS):
            brave_update_desc = f'Brave Update ({user_or_machine_desc})'
            if is_brave_update_installed(is_user):
                if not is_user and not is_user_an_admin():
                    print(f'Cannot uninstall {brave_update_desc}. Please re-run as admin.')
                else:
                    uninstall_brave_update(is_user)
                    print('Uninstalled %s.' % brave_update_desc)
            else:
                print(brave_update_desc + ' is not installed.')

def uninstall_brave(is_user, channel):
    uninstall_string = get_brave_uninstall_string(is_user, channel)
    cp = run(uninstall_string + ' --force-uninstall')
    if cp.returncode not in (0, 19):
        if is_brave_installed(is_user, channel):
            # Raise an error.
            cp.check_returncode()

def get_brave_uninstall_string(is_user, channel):
    uninstall_key = WINDOWS_UNINSTALL_KEY
    if is_user:
        uninstall_key = uninstall_key.replace('WOW6432Node\\', '')
    uninstall_key += '\\' + BRAVE_UNINSTALL_SUBKEYS[channel]
    hklm_hkcu = HKEY_CURRENT_USER if is_user else HKEY_LOCAL_MACHINE
    with OpenKey(hklm_hkcu, uninstall_key) as key:
        return QueryValueEx(key, 'UninstallString')[0]

def is_brave_installed(is_user, channel):
    try:
        get_brave_uninstall_string(is_user, channel)
    except FileNotFoundError:
        return False
    return True

def uninstall_brave_update(is_user):
    pardir = os.getenv('LOCALAPPDATA' if is_user else 'PROGRAMFILES(X86)')
    run([get_brave_update_exe(is_user), '/uninstall'])

def is_brave_update_installed(is_user):
    return exists(get_brave_update_exe(is_user))

def get_brave_update_exe(is_user):
    pardir = os.getenv('LOCALAPPDATA' if is_user else 'PROGRAMFILES(X86)')
    return join(pardir, r'BraveSoftware\Update\BraveUpdate.exe')

def is_user_an_admin():
    return ctypes.windll.shell32.IsUserAnAdmin() != 0

def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        '--channel', choices=['all'] + ALL_CHANNELS, default='all'
    )
    parser.add_argument(
        '--user_or_machine', choices=['both', 'user', 'machine'], default='both'
    )
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

    return channels, uninstall_user_or_machine

if __name__ == '__main__':
    main()
