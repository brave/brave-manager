from contextlib import contextmanager
from os import getpid, listdir
from os.path import join
from shutil import copytree
from subprocess import run, DEVNULL
from time import time
from tqdm import tqdm

import questionary
import requests
import sys

def select(message, choices, instruction=' '):
    question = questionary.select(
        message, choices, use_shortcuts=True, instruction=instruction
    )
    return question.ask()

def download_file(url, path):
    print(f'Downloading {url}:')
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024
    progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
    with open(path, 'wb') as f:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            f.write(data)
    progress_bar.close()

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
