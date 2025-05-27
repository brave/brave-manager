from os import makedirs
from os.path import dirname, join
from os.path import getsize
from shutil import rmtree

import os

CACHE_DIR = join(dirname(dirname(dirname(__file__))), '.cache')

def prepare(path_in_cache):
    absolute_path = join(CACHE_DIR, path_in_cache)
    makedirs(dirname(absolute_path), exist_ok=True)
    return absolute_path

def get_size():
    result = 0
    for parent_dir, _, files in os.walk(CACHE_DIR):
        for file_name in files:
            result += getsize(join(parent_dir, file_name))
    return result

def clear():
    try:
        rmtree(CACHE_DIR)
    except FileNotFoundError:
        pass
