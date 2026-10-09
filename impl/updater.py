import sys

if sys.platform == 'win32':
    from impl.win.updater import UPDATERS
else:
    from impl.mac.updater import UPDATERS

def get_updaters_to_uninstall():
    return [
        app for updater in UPDATERS for app in updater.get_apps()
        if app.is_installed or app.has_remnants
    ]
