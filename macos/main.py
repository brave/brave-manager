from impl import brave, cache, CHANNELS, updater
from impl.actions import Uninstall, Install, Launch, ClearCache, \
    UninstallUpdater, DeleteProfile
from impl.cache import CACHE_DIR
from impl.releases import get_releases, group_by_minor_version
from impl.util import select, human_readable_size
from os.path import expanduser

import re

def main():
    try:
        actions = []
        main_action = ask_main_action()
        profiles = brave.get_existing_profiles()
        if main_action == 'install':
            channel, is_installed = ask_channel()
            if not channel:
                return
            public_only = ask_public_only()
            version, dmg_url = ask_dmg_to_install(channel, public_only)
            if is_installed:
                actions.append(Uninstall(channel))
            if channel in profiles and ask_delete_profile():
                actions.append(DeleteProfile(channel))
            actions.append(Install(channel, version, dmg_url))
            if ask_launch_after_install():
                actions.append(Launch(channel))
        elif main_action == 'uninstall':
            channel = ask_channel(installed_only=True)
            if not channel:
                return
            actions.append(Uninstall(channel))
            if channel in profiles and ask_delete_profile():
                actions.append(DeleteProfile(channel))
        elif main_action == 'delete_profile':
            if not profiles:
                print("You don't have any profiles to delete.")
                return
            profile = ask_which_profile_to_delete(profiles)
            if not profile:
                return
            actions.append(DeleteProfile(profile))
        elif main_action == 'launch':
            channel = ask_channel(installed_only=True)
            if not channel:
                return
            Launch(channel)()
            return
        elif main_action == 'uninstall_updater':
            installed_updaters = updater.get_installed_updaters()
            if not installed_updaters:
                print("You don't have Brave Updater installed.")
                return
            to_uninstall = ask_which_updater_to_uninstall(installed_updaters)
            if not to_uninstall:
                return
            actions.append(UninstallUpdater(to_uninstall))
        elif main_action == 'clear_cache':
            actions.append(ClearCache())
        if ask_confirm_actions(actions):
            for action in actions:
                action()
    except KeyboardInterrupt:
        pass

def ask_main_action():
    message = 'What do you want to do?'
    instruction = '(press ctrl+c to cancel)'
    cache_size_text = human_readable_size(cache.get_size())
    cache_dir = CACHE_DIR.replace(expanduser('~'), '~')
    choices = {
        'Install a new version of Brave': 'install',
        'Uninstall Brave': 'uninstall',
        'Delete a profile': 'delete_profile',
        'Launch Brave': 'launch',
        'Uninstall Brave Updater': 'uninstall_updater',
        f'Clear the cache ({cache_size_text} in {cache_dir})': 'clear_cache'
    }
    choice_text = select(message, choices, instruction)
    if choice_text is None:
        raise KeyboardInterrupt
    return choices[choice_text]

def ask_channel(installed_only=False):
    installed_channels = brave.get_installed_channels()
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
    choice = choices[choice_text]
    return choice[0] if installed_only else choice

def ask_public_only():
    message = 'Should the version you want to install be public?'
    choice = select(message, ['yes', 'no'])
    if choice is None:
        raise KeyboardInterrupt
    return choice == 'yes'

def ask_dmg_to_install(channel, public_only):
    releases = get_releases(channel, public_only)
    minor_releases = group_by_minor_version(releases)
    while True:
        message = 'Which release do you want to install?'
        minor_version = select(message, sort_minor_versions(minor_releases))
        if minor_version is None:
            raise KeyboardInterrupt

        message = 'Which exact version?'
        releases = {
            _get_release_title(r, channel): r
            for r in minor_releases[minor_version]
        }
        release_title = select(message, sort_versions(releases))
        if release_title is None:
            continue

        release = releases[release_title]
        installers = release['installers']
        message = 'Which installer do you want to use?'
        installer_name = select(message, installers)
        if installer_name:
            return release['version'], installers[installer_name]

def ask_delete_profile():
    message = 'Do you also want to delete the profile?'
    choice = select(message, ['no', 'yes'])
    if choice is None:
        raise KeyboardInterrupt
    return choice == 'yes'

def ask_launch_after_install():
    message = 'Should the app be launched after installation?'
    choice = select(message, ['yes', 'no'])
    if choice is None:
        raise KeyboardInterrupt
    return choice == 'yes'

def ask_which_profile_to_delete(profiles):
    message = 'Which profile do you want to delete?'
    choices = {profile.title(): profile for profile in profiles}
    choice = select(message, choices)
    if choice is None:
        raise KeyboardInterrupt
    return choices[choice]

def ask_which_updater_to_uninstall(installed_updaters):
    message = 'Which updater do you want to uninstall?'
    choice = select(message, installed_updaters)
    if choice is None:
        raise KeyboardInterrupt
    return choice

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

def sort_minor_versions(versions):
    parse_minor_version = lambda v: tuple(map(int, v.split('.')[:2]))
    return sorted(versions, key=parse_minor_version, reverse=True)

def sort_versions(releases):
    parse_version = lambda v: tuple(map(int, v.split('.')))
    get_version_tuple = lambda v: parse_version(releases[v]['version'])
    return sorted(releases, key=get_version_tuple, reverse=True)

def _get_release_title(r, channel):
    result = r['name'].replace(f'{channel.title()} ', '')
    result = re.sub(r'^v', '', result)
    result = result.replace(' (Chromium', ', Chromium').replace(')', '')
    result += ', ' + r['published_at'].split('T')[0]
    return result

if __name__ == "__main__":
    main()
