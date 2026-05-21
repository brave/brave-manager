from impl import brave, cache, updater
from impl.actions import Uninstall, Install, Launch, ClearCache, \
    UninstallUpdater, DeleteProfile
from impl.brave import PRODUCTS
from impl.cache import CACHE_DIR
from impl.releases import get_releases, group_by_minor_version
from impl.util import select, human_readable_size
from os.path import expanduser

import re

def main():
    try:
        actions = []
        main_action = ask_main_action()
        apps_with_profiles = brave.get_apps_with_profiles()
        if main_action == 'install':
            product = ask_product()
            if not product:
                return
            app = ask_app(product)
            if not app:
                return
            public_only = ask_public_only()
            version, dmg_url = ask_dmg_to_install(app, public_only)
            if app.is_installed:
                actions.append(Uninstall(app))
            if app in apps_with_profiles and ask_delete_profile():
                actions.append(DeleteProfile(app))
            actions.append(Install(version, dmg_url))
            if ask_launch_after_install():
                actions.append(Launch(app))
        elif main_action == 'uninstall':
            product = ask_product()
            if not product:
                return
            app = ask_app(product, installed_only=True)
            if not app:
                return
            actions.append(Uninstall(app))
            if app in apps_with_profiles and ask_delete_profile():
                actions.append(DeleteProfile(app))
        elif main_action == 'delete_profile':
            if not apps_with_profiles:
                print("You don't have any profiles to delete.")
                return
            app = ask_which_profile_to_delete(apps_with_profiles)
            if not app:
                return
            actions.append(DeleteProfile(app))
        elif main_action == 'launch':
            product = ask_product()
            if not product:
                return
            app = ask_app(product, installed_only=True)
            if not app:
                return
            Launch(app)()
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
        'Install': 'install',
        'Uninstall': 'uninstall',
        'Launch': 'launch',
        'Delete a profile': 'delete_profile',
        'Uninstall Brave Updater': 'uninstall_updater',
        f'Clear the cache ({cache_size_text} in {cache_dir})': 'clear_cache'
    }
    choice_text = select(message, choices, instruction)
    if choice_text is None:
        raise KeyboardInterrupt
    return choices[choice_text]

def ask_product():
    message = 'Which product?'
    choices = PRODUCTS
    choice_text = select(message, choices)
    if choice_text is None:
        raise KeyboardInterrupt
    return choices[choice_text]

def ask_app(product, installed_only=False):
    choices = {}
    for channel in product.channels:
        app = product(channel)
        if app.is_installed:
            version = app.version
            version_text = f'installed at {version}' if version else 'installed'
        elif installed_only:
            continue
        else:
            version_text = 'not installed'
        choices[f'{channel.title()} ({version_text})'] = app
    if not choices:
        print(f"You don't have any installed versions of {product}.")
        return None
    choice_text = select('Which channel?', choices)
    if choice_text is None:
        raise KeyboardInterrupt
    return choices[choice_text]

def ask_public_only():
    message = 'Should the version you want to install be public?'
    choice = select(message, ['yes', 'no'])
    if choice is None:
        raise KeyboardInterrupt
    return choice == 'yes'

def ask_dmg_to_install(app, public_only):
    releases = get_releases(app, public_only)
    minor_releases = group_by_minor_version(releases)
    while True:
        message = 'Which release do you want to install?'
        minor_version = select(message, sort_minor_versions(minor_releases))
        if minor_version is None:
            raise KeyboardInterrupt

        message = 'Which exact version?'
        releases = {
            _get_release_title(r, app.channel): r
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

def ask_which_profile_to_delete(apps):
    message = 'Which profile do you want to delete?'
    choices = {str(app): app for app in apps}
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
