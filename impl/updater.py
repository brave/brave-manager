import sys

if sys.platform == 'win32':
    from impl.win.updater import UPDATERS
else:
    from impl.mac.updater import UPDATERS

def get_installed_updaters():
    return [
        app for updater in UPDATERS for app in updater.get_apps()
        if app.is_installed
    ]
