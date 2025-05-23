from os.path import join, dirname, exists, expanduser
from subprocess import run

def main():
    ensure_venv_exists()
    install_dependencies()
    add_to_zshrc()
    print("Done. Please type the following for the changes to take effect:")
    print("    source ~/.zshrc")
    print("Then you can run Brave Manager by typing 'bm' in your Terminal.")

def ensure_venv_exists():
    venv_dir = get_project_file('venv')
    if not exists(venv_dir):
        run(['python3', '-m', 'venv', venv_dir])

def install_dependencies():
    pip = get_project_file('venv', 'bin', 'pip')
    requirements_txt = get_project_file('macos', 'requirements.txt')
    run([pip, 'install', '-U', 'pip'])
    run([pip, 'install', '-Ur', requirements_txt])

def add_to_zshrc():
    zshrc = expanduser('~/.zshrc')
    new_zshrc_lines = []
    found_bm_alias = False
    bm_alias_line = get_bm_alias() + '\n'
    try:
        with open(zshrc) as f:
            for line in f:
                if line.startswith('alias bm='):
                    found_bm_alias = True
                    line = bm_alias_line
                new_zshrc_lines.append(line)
    except FileNotFoundError:
        pass
    if not found_bm_alias:
        new_zshrc_lines.append(bm_alias_line)
    with open(zshrc, 'w') as f:
        for line in new_zshrc_lines:
            f.write(line)

def get_bm_alias():
    python = get_project_file('venv/bin/python')
    main_py = get_project_file('macos/main.py')
    return f"alias bm='\"{python}\" \"{main_py}\"'"

def get_project_file(*relpath):
    project_dir = dirname(dirname(__file__))
    return join(project_dir, *relpath)

if __name__ == '__main__':
    main()
