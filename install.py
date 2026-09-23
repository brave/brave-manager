from os.path import join, dirname, exists, expanduser
from subprocess import run

import sys

def main():
    ensure_venv_exists()
    install_dependencies()
    bin_dir = get_project_file('bin')
    # Don't touch the PATH when run non-interactively, eg. from CI:
    if sys.stdin.isatty() and ask_yes_no(f'Add {bin_dir} to your PATH?'):
        add_to_path(bin_dir)
        print(
            'Done. Open a new terminal. Then you can run Brave Manager by '
            "typing 'bm'."
        )
    else:
        bm = join(bin_dir, 'bm.bat' if sys.platform == 'win32' else 'bm')
        print(f'Done. You can run Brave Manager via {bm}.')

def ensure_venv_exists():
    venv_dir = get_project_file('venv')
    if not exists(venv_dir):
        run([sys.executable, '-m', 'venv', venv_dir], check=True)

def install_dependencies():
    if sys.platform == 'win32':
        python = get_project_file('venv', 'Scripts', 'python.exe')
    else:
        python = get_project_file('venv', 'bin', 'python')
    requirements_txt = get_project_file('requirements.txt')
    run([python, '-m', 'pip', 'install', '-U', 'pip'], check=True)
    run([python, '-m', 'pip', 'install', '-Ur', requirements_txt], check=True)

def ask_yes_no(question):
    while True:
        answer = input(f'{question} [y/n] ').strip().lower()
        if answer in ('y', 'yes'):
            return True
        if answer in ('n', 'no'):
            return False

def add_to_path(bin_dir):
    if sys.platform == 'win32':
        add_to_windows_path(bin_dir)
    else:
        add_to_zshrc(bin_dir)

def add_to_windows_path(bin_dir):
    from winreg import OpenKey, QueryValueEx, SetValueEx, HKEY_CURRENT_USER, \
        KEY_READ, KEY_WRITE, REG_EXPAND_SZ
    import ctypes
    with OpenKey(HKEY_CURRENT_USER, 'Environment', 0, KEY_READ) as key:
        try:
            path, value_type = QueryValueEx(key, 'Path')
        except FileNotFoundError:
            path, value_type = '', REG_EXPAND_SZ
    entries = [entry for entry in path.split(';') if entry]
    if bin_dir.lower() in (entry.lower() for entry in entries):
        return
    entries.append(bin_dir)
    with OpenKey(HKEY_CURRENT_USER, 'Environment', 0, KEY_WRITE) as key:
        SetValueEx(key, 'Path', 0, value_type, ';'.join(entries))
    # Without this, new terminals only see the new PATH after signing out:
    HWND_BROADCAST, WM_SETTINGCHANGE, SMTO_ABORTIFHUNG = 0xFFFF, 0x1A, 0x2
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment', SMTO_ABORTIFHUNG,
        5000, None
    )

def add_to_zshrc(bin_dir):
    zshrc = expanduser('~/.zshrc')
    path_line = f'export PATH="$PATH:{bin_dir}"\n'
    try:
        with open(zshrc) as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []
    if path_line not in lines:
        lines.append(path_line)
    with open(zshrc, 'w') as f:
        f.writelines(lines)

def get_project_file(*relpath):
    project_dir = dirname(__file__)
    return join(project_dir, *relpath)

if __name__ == '__main__':
    main()
