from argparse import ArgumentParser
from impl import brave, cache, updater
from impl.actions import Uninstall, Launch, ClearCache, DeleteProfile
from impl.brave import PRODUCTS
from impl.browser import Browser
from impl.updater import UPDATERS
from impl.cache import CACHE_DIR
from impl.releases import get_releases, group_by_minor_version
from impl.util import select, human_readable_size
from os.path import expanduser

import re

def main():
    args = parse_args()
    try:
        if args.command == 'uninstall':
            if args.target == 'updater':
                uninstall_updaters(args.updaters)
            else:
                uninstall(args.product, args.channel, args.delete_profile)
        else:
            run_interactively()
    except KeyboardInterrupt:
        pass

def parse_args(argv=None):
    parser = ArgumentParser(
        description='Manage installed Brave versions. Without a command, '
        'Brave Manager asks what to do.'
    )
    subparsers = parser.add_subparsers(dest='command')
    uninstall_parser = subparsers.add_parser(
        'uninstall', help='uninstall a browser channel or an updater'
    )
    targets = uninstall_parser.add_subparsers(dest='target', required=True)
    for title, product in PRODUCTS.items():
        product_parser = targets.add_parser(
            title.lower(),
            help=f'uninstall a {title} channel, all architectures and levels'
        )
        product_parser.add_argument(
            'channel', type=str.lower, choices=Browser.CHANNELS
        )
        product_parser.add_argument(
            '--delete-profile', action='store_true',
            help='also delete the profile'
        )
        product_parser.set_defaults(product=product)
    updaters = {
        u.product_title.replace(' ', '').lower(): u for u in UPDATERS
    }
    updater_parser = targets.add_parser(
        'updater', help='uninstall all installed updaters, or just one'
    )
    updater_parser.add_argument(
        'name', nargs='?', type=str.lower, choices=list(updaters)
    )
    args = parser.parse_args(argv)
    if args.command == 'uninstall' and args.target == 'updater':
        if args.name:
            args.updaters = [updaters[args.name]]
        else:
            args.updaters = list(UPDATERS)
    return args

def uninstall(product, channel, delete_profile):
    apps = [app for app in product.get_apps() if app.channel == channel]
    installed = [app for app in apps if app.is_installed]
    for app in installed:
        Uninstall(app)()
    if not installed:
        print(f'{apps[0].title} is not installed.')
    if delete_profile:
        # All architectures and levels of a channel share one profile:
        app = apps[0]
        if app.has_profile:
            DeleteProfile(app)()
        else:
            print(f'{app.title} has no profile.')

def uninstall_updaters(updaters):
    installed = [
        app for updater in updaters for app in updater.get_apps()
        if app.is_installed
    ]
    for app in installed:
        Uninstall(app)()
    if not installed:
        print('No updaters are installed.')

def run_interactively():
    try:
        actions = []
        main_action = ask_main_action()
        if main_action == 'install':
            product = ask_product()
            channel = ask_channel(product)
            architecture = ask_architecture(product)
            is_system_level = ask_is_system_level()
            app = product(is_system_level, architecture, channel)
            public_only = ask_public_only()
            version, installer_url = ask_installer_to_install(app, public_only)
            if app.is_installed:
                actions.append(Uninstall(app))
            if app.has_profile and ask_delete_profile():
                actions.append(DeleteProfile(app))
            actions.append(app.create_install_action(version, installer_url))
            if ask_launch_after_install():
                actions.append(Launch(app))
        elif main_action == 'uninstall':
            product = ask_product()
            app = ask_installed_app(product)
            if not app:
                return
            actions.append(Uninstall(app))
            if app.has_profile and ask_delete_profile():
                actions.append(DeleteProfile(app))
        elif main_action == 'delete_profile':
            apps_with_profiles = brave.get_apps_with_profiles()
            if not apps_with_profiles:
                print("You don't have any profiles to delete.")
                return
            app = ask_which_profile_to_delete(apps_with_profiles)
            if not app:
                return
            actions.append(DeleteProfile(app))
        elif main_action == 'launch':
            product = ask_product()
            app = ask_installed_app(product)
            if not app:
                return
            Launch(app)()
            return
        elif main_action == 'uninstall_updater':
            installed_updaters = updater.get_installed_updaters()
            if not installed_updaters:
                print("You don't have any updaters installed.")
                return
            to_uninstall = ask_which_updater_to_uninstall(installed_updaters)
            if not to_uninstall:
                return
            actions.append(Uninstall(to_uninstall))
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
        'Uninstall an updater': 'uninstall_updater',
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

def ask_channel(product):
    choices = {
        channel.title(): channel for channel in product.INSTALLABLE_CHANNELS
    }
    choice_text = select('Which channel?', choices)
    if choice_text is None:
        raise KeyboardInterrupt
    return choices[choice_text]

def ask_architecture(product):
    choice = select('Which architecture?', product.SUPPORTED_ARCHITECTURES)
    if choice is None:
        raise KeyboardInterrupt
    return choice

def ask_is_system_level():
    message = 'Install for the current user or system-wide?'
    choices = {'current user': False, 'system-wide': True}
    choice_text = select(message, choices)
    if choice_text is None:
        raise KeyboardInterrupt
    return choices[choice_text]

def ask_installed_app(product):
    choices = {}
    for app in product.get_apps():
        if app.is_installed:
            version = app.version
            version_text = f'installed at {version}' if version else 'installed'
            choices[f'{app.name} ({version_text})'] = app
    if not choices:
        title = product.product_title
        print(f"You don't have any installed versions of {title}.")
        return None
    choice_text = select('Which installation?', choices)
    if choice_text is None:
        raise KeyboardInterrupt
    return choices[choice_text]

def ask_public_only():
    message = 'Must the version you want to install be public?'
    choice = select(message, ['yes', 'no'])
    if choice is None:
        raise KeyboardInterrupt
    return choice == 'yes'

def ask_installer_to_install(app, public_only):
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
        # Each app accepts exactly one installer per release:
        installer_url, = release['installers'].values()
        return release['version'], installer_url

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
    choices = {app.title: app for app in apps}
    choice = select(message, choices)
    if choice is None:
        raise KeyboardInterrupt
    return choices[choice]

def ask_which_updater_to_uninstall(installed_updaters):
    message = 'Which updater do you want to uninstall?'
    choices = {str(app): app for app in installed_updaters}
    choice = select(message, choices)
    if choice is None:
        raise KeyboardInterrupt
    return choices[choice]

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
