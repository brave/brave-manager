from impl import CHANNELS
from os.path import exists, join
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
