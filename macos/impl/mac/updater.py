from os.path import expanduser, exists
from shutil import rmtree
from subprocess import run

_UPDATER_PATH = '/Library/Application Support/BraveSoftware/BraveUpdater'
UPDATER_PATHS = {
    'system': _UPDATER_PATH,
    'user': expanduser(f'~{_UPDATER_PATH}')
}

UPDATER_EXECUTABLE = '/Current/BraveUpdater.app/Contents/MacOS/BraveUpdater'

def get_installed_updaters():
    return [
        scope for scope, path in UPDATER_PATHS.items()
        if exists(path)
    ]

def uninstall(scope):
    updater_path = UPDATER_PATHS[scope]
    updater_executable = updater_path + UPDATER_EXECUTABLE
    if exists(updater_executable):
        args = [updater_executable, '--uninstall']
        if scope == 'system':
            args.append('--system')
        run(args, check=True)
    rmtree(updater_path)
