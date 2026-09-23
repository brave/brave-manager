from subprocess import run

def run_elevated(command, cwd=None):
    run(['sudo', *command], cwd=cwd)
