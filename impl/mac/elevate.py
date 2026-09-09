from subprocess import run

def run_elevated(command, cwd):
    run(['sudo', *command], cwd=cwd)
