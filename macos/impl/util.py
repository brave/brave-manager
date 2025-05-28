from contextlib import contextmanager
from os import getpid, listdir
from os.path import join
from shutil import copytree
from subprocess import run, DEVNULL
from time import time

import questionary
import requests
import re
import sys

def extract_version(tag_name):
    match = re.match(r'v(\d+\.\d+\.\d+)', tag_name)
    if not match:
        raise ValueError(f'Invalid tag name: {tag_name}')
    return match.group(1)

def select(message, choices, instruction=' '):
    question = questionary.select(
        message, choices, use_shortcuts=True, instruction=instruction
    )
    return question.ask()

class FileDownloader:
    def __init__(self, url, path):
        self.url = url
        self.path = path
        self.response = None
    def start(self):
        self.response = requests.get(self.url, stream=True)
        return int(self.response.headers.get('content-length', 0))
    def run(self, block_size=1024):
        with open(self.path, 'wb') as f:
            for data in self.response.iter_content(block_size):
                f.write(data)
                yield len(data)

def install_dmg(dmg_path):
    mount_point = f'/Volumes/temp_{getpid()}_{int(time())}'
    _run('hdiutil', 'attach', dmg_path, '-nobrowse', '-mountpoint', mount_point)
    try:
        app_name = [f for f in listdir(mount_point) if f.endswith('.app')][0]
        src_path = join(mount_point, app_name)
        dst_path = join('/Applications', app_name)
        copytree(src_path, dst_path, symlinks=True)
    finally:
        _run('hdiutil', 'detach', mount_point)

@contextmanager
def print_done(message):
    sys.stdout.write(f'{message}...')
    sys.stdout.flush()
    yield
    sys.stdout.write(' done.\n')

def _run(*args):
    run(args, check=True, stdout=DEVNULL, stderr=DEVNULL)
