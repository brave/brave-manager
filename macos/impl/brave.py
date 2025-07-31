from impl import CHANNELS
from os import remove
from os.path import exists, isdir, join, expanduser
from plistlib import load
from shutil import rmtree
from subprocess import run

def get_installed_channels():
    result = {}
    for channel in CHANNELS:
        app_dir = get_app_dir(channel)
        if not exists(app_dir):
            continue
        try:
            version = get_version(app_dir)
        except FileNotFoundError:
            version = None
        result[channel] = version
    return result

def uninstall(channel):
    rmtree(get_app_dir(channel))

def launch(channel):
    run(['open', '-a', get_app_dir(channel)])

def get_app_dir(channel):
    if channel == 'release':
        suffix = ''
    else:
        suffix = f' {channel.title()}'
    return join('/Applications', f'Brave Browser{suffix}.app')

def get_version(app_dir):
    info_plist_path = join(app_dir, 'Contents', 'Info.plist')
    with open(info_plist_path, 'rb') as f:
        plist = load(f)
    version_chromium = plist['CFBundleShortVersionString']
    return version_chromium.split('.', 1)[1]

def get_existing_profiles():
    result = []
    for channel in CHANNELS:
        for path in get_profile_paths(channel):
            if exists(path):
                result.append(channel)
                break
    return result

def delete_profile(channel):
    for path in get_profile_paths(channel):
        if isdir(path):
            rmtree(path)
        elif exists(path):
            remove(path)

def get_profile_paths(channel):
    if channel == 'release':
        dash_suffix = ''
        dot_suffix = ''
    else:
        dash_suffix = f'-{channel.title()}'
        dot_suffix = f'.{channel}'
    return list(map(lambda p: expanduser(f'~/Library/{p}'), [
        f'Application Support/BraveSoftware/Brave-Browser{dash_suffix}',
        f'Caches/BraveSoftware/Brave-Browser{dash_suffix}',
        f'Saved Application State/com.brave.Browser{dot_suffix}.savedState',
        f'Caches/com.brave.Browser{dot_suffix}',
        f'Preferences/com.brave.Browser{dot_suffix}.plist',
    ]))
