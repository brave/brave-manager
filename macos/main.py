from impl import brave, cache, CHANNELS
from impl.actions import Uninstall, Install, Launch, ClearCache
from impl.releases import get_releases
from impl.util import select

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
    return choices[choice_text]

def ask_public_only():
    message = 'Should the version you want to install be public?'
    choice = select(message, ['yes', 'no'])
    if choice is None:
        raise KeyboardInterrupt
    return choice == 'yes'

def ask_dmg_to_install(channel, public_only):
    releases = get_releases(
        channel, public_only, MAX_NUM_CHOICES_SUPPORTED_BY_QUESTIONARY_SELECT
    )
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

if __name__ == "__main__":
    main()
