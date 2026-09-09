from contextlib import contextmanager

import questionary
import requests
import re
import sys

MAX_NUM_CHOICES_SUPPORTED_BY_QUESTIONARY_SELECT = 36

def extract_version(tag_name):
    match = re.match(r'v(\d+\.\d+\.\d+)', tag_name)
    if not match:
        raise ValueError(f'Invalid tag name: {tag_name}')
    return match.group(1)

def select(message, choices, instruction=' '):
    use_shortcuts = \
        len(choices) <= MAX_NUM_CHOICES_SUPPORTED_BY_QUESTIONARY_SELECT
    question = questionary.select(
        message, choices, use_shortcuts=use_shortcuts, instruction=instruction
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

@contextmanager
def print_done(message):
    sys.stdout.write(f'{message}...')
    sys.stdout.flush()
    yield
    sys.stdout.write(' done.\n')

def human_readable_size(size_bytes):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if size_bytes < 1_000:
            if size_bytes < 100 and size_bytes != int(size_bytes):
                num_decimals = 2
            else:
                num_decimals = 0
            return f'{size_bytes:.{num_decimals}f} {unit}'
        size_bytes /= 1_000
