from contextlib import contextmanager
from impl import cache
from os import getpid, listdir
from os.path import exists, join
from plistlib import load
from shutil import rmtree, copytree
from subprocess import run, DEVNULL
from time import time
from tqdm import tqdm

import json
import questionary
import requests
import sys

CHANNELS = ('nightly', 'beta', 'release')
MAX_NUM_CHOICES_SUPPORTED_BY_QUESTIONARY_SELECT = 36

def main():
    try:
        actions = []
        main_action = ask_main_action()
        if main_action == 'install':
            channel, is_installed = ask_channel()
            if not channel:
                return
            public_only = ask_public_only()
            version, dmg_url = ask_dmg_to_install(channel, public_only)
            if is_installed:
                actions.append(Uninstall(channel))
            actions.append(Install(channel, version, dmg_url))
            launch_after_install = ask_launch_after_install()
            if launch_after_install:
                actions.append(Launch(channel))
        elif main_action == 'uninstall':
            channel = ask_channel(installed_only=True)
            if not channel:
                return
            actions.append(Uninstall(channel[0]))
        elif main_action == 'launch':
            channel = ask_channel(installed_only=True)
            if not channel:
                return
            Launch(channel[0])()
            return
        elif main_action == 'clear_cache':
            actions.append(ClearCache())
        if ask_confirm_actions(actions):
            for action in actions:
                action()
    except KeyboardInterrupt:
        pass

class Uninstall:
    def __init__(self, channel):
        self.channel = channel
    def __str__(self):
        return f'Uninstall {self.channel.title()}'
    def __call__(self):
        with print_done(f'Uninstalling {self.channel.title()}'):
            rmtree(get_app_dir(self.channel))

class Install:
    def __init__(self, channel, version, dmg_url):
        self.channel = channel
        self.version = version
        self.dmg_url = dmg_url
    def __str__(self):
        return f'Install {self.channel.title()} {self.version}'
    def __call__(self):
        cache_path = cache.prepare(self.dmg_url.split('//', 1)[1])
        if not exists(cache_path):
            download_file(self.dmg_url, cache_path)
        with print_done(f'Installing {self.channel.title()}'):
            install_dmg(cache_path)

class Launch:
    def __init__(self, channel):
        self.channel = channel
    def __str__(self):
        return f'Launch {self.channel.title()}'
    def __call__(self):
        run(['open', '-a', get_app_dir(self.channel)])

class ClearCache:
    def __str__(self):
        return 'Clear the cache'
    def __call__(self):
        cache.clear()

def ask_main_action():
    message = 'What do you want to do?'
    instruction = '(press ctrl+c to cancel)'
    cache_size_bytes = cache.get_size()
    cache_size_text = f'{cache_size_bytes // (1024 * 1024)} MB'
    choices = {
        'Install a new version of Brave': 'install',
        'Uninstall Brave': 'uninstall',
        'Launch Brave': 'launch',
        f'Clear the cache ({cache_size_text})': 'clear_cache'
    }
    choice_text = select(message, choices, instruction)
    if choice_text is None:
        raise KeyboardInterrupt
    return choices[choice_text]

def ask_channel(installed_only=False):
    installed_channels = get_installed_channels()
    choices = {}
    for channel in CHANNELS:
        try:
            version = installed_channels[channel]
        except KeyError:
            if installed_only:
                continue
            version_text = 'not installed'
            is_installed = False
        else:
            version_text = 'installed'
            if version:
                version_text += f' at {version}'
            is_installed = True
        choice_text = f'{channel.title()} ({version_text})'
        choices[choice_text] = channel, is_installed
    if not choices:
        print("You don't have any installed versions of Brave.")
        return None
    message = 'Which channel?'
    choice_text = select(message, choices)
    if choice_text is None:
        raise KeyboardInterrupt
    return choices[choice_text]

def ask_public_only():
    message = 'Should the version you want to install be public?'
    choice = select(message, ['yes', 'no'])
    if choice is None:
        raise KeyboardInterrupt
    return choice == 'yes'

def ask_dmg_to_install(channel, public_only):
    releases = get_releases(channel, public_only)
    while True:
        message = 'Which version do you want to install?'
        version = select(message, releases)
        if version is None:
            raise KeyboardInterrupt
        dmgs = dict(sorted(releases[version].items()))
        message = 'Which dmg do you want to install?'
        dmg_name = select(message, dmgs)
        if dmg_name:
            return version, dmgs[dmg_name]

def ask_launch_after_install():
    message = 'Should the app be launched after installation?'
    choice = select(message, ['yes', 'no'])
    if choice is None:
        raise KeyboardInterrupt
    return choice == 'yes'

def ask_confirm_actions(actions):
    message_parts = ['I will perform the following actions:']
    indent = '  '
    for action in actions:
        message_parts.append(f'{indent}* {action}')
    message_parts.append(f'{indent}Do you want to continue?')
    message = '\n'.join(message_parts)
    choices = ['yes', 'no']
    choice = select(message, choices)
    return choice == choices[0]

def get_releases(
    channel, public_only,
    max_num=MAX_NUM_CHOICES_SUPPORTED_BY_QUESTIONARY_SELECT
):
    result = {}
    for release in _cache_releases():
        if not release['name'].startswith(channel.title()):
            continue
        if public_only and release['prerelease']:
            continue
        tag_name = release['tag_name']
        if not tag_name.startswith('v'):
            continue
        version = tag_name[1:]
        dmgs_this_version = {
            asset['name']: asset['browser_download_url']
            for asset in release['assets'] if asset['name'].endswith('.dmg')
        }
        if dmgs_this_version:
            result[version] = dmgs_this_version
            if len(result) == max_num:
                break
    return result

def _cache_releases():
    cache_path = cache.prepare('releases.json')
    try:
        with open(cache_path, 'rb') as f:
            cached_releases = json.load(f)
    except FileNotFoundError:
        cached_releases = {}
    new_items = {}
    rest_is_in_cache = False
    try:
        for page_results in _paginate_releases():
            for release in page_results:
                # Need str(...) because we want to use cache_id as a key in
                # JSON, where keys must be strings.
                cache_id = str(release['id'])
                if cache_id in cached_releases:
                    rest_is_in_cache = True
                    break
                else:
                    release_thin = {
                        'name': release['name'],
                        'tag_name': release['tag_name'],
                        'prerelease': release['prerelease'],
                        'assets': [
                            {
                                'name': asset['name'],
                                'browser_download_url':
                                    asset['browser_download_url']
                            }
                            for asset in release['assets']
                        ]
                    }
                    new_items[cache_id] = release_thin
                    yield release_thin
            if rest_is_in_cache:
                break
        yield from cached_releases.values()
    except GeneratorExit:
        cached_releases.update(new_items)
        with open(cache_path, 'w') as f:
            json.dump(cached_releases, f)

def _paginate_releases():
    for page in range(1, sys.maxsize):
        url = f'https://api.github.com/repos/brave/brave-browser/releases?' \
              f'per_page=100&page={page}'
        response = requests.get(url)
        response.raise_for_status()
        yield response.json()

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

def select(message, choices, instruction=' '):
    question = questionary.select(
        message, choices, use_shortcuts=True, instruction=instruction
    )
    return question.ask()

def download_file(url, path):
    print(f'Downloading {url}:')
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024
    progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
    with open(path, 'wb') as f:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            f.write(data)
    progress_bar.close()

def install_dmg(dmg_path):
    mount_point = f'/Volumes/temp_{getpid()}_{int(time())}'
    _run('hdiutil', 'attach', dmg_path, '-nobrowse', '-mountpoint', mount_point)
    try:
        app_name = [f for f in listdir(mount_point) if f.endswith('.app')][0]
        src_path = join(mount_point, app_name)
        dst_path = join('/Applications', app_name)
        copytree(src_path, dst_path, symlinks=True)
    finally:
        _run('hdiutil', 'detach', mount_point)

@contextmanager
def print_done(message):
    sys.stdout.write(f'{message}...')
    sys.stdout.flush()
    yield
    sys.stdout.write(' done.\n')

def _run(*args):
    run(args, check=True, stdout=DEVNULL, stderr=DEVNULL)

if __name__ == "__main__":
    main()
