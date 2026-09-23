from os import geteuid
from subprocess import run

def is_elevated():
    return geteuid() == 0

def run_elevated(command, cwd=None):
    run(['sudo', *command], cwd=cwd)
