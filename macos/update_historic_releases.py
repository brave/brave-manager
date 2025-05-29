"""
This script updates the historic releases compressed JSON file. It's used to
keep track of older releases that are not available via the Github API.

It's run manually, and the output is committed to the repo.

Usage:
    python update_historic_releases.py /path/to/brave-core GITHUB_TOKEN
"""

from argparse import ArgumentParser
from impl.util import extract_version
from impl.releases import update_historic_releases
from subprocess import check_output
from time import sleep
from tqdm import tqdm

import os
import sys

def main():
    brave_core_path, github_token, clear_existing = parse_args_and_env()
    tags = get_tags_most_recent_first(brave_core_path)
    version_tags = extract_version_tags(tags)
    version_tags_iter = tqdm(version_tags, desc='Fetching historic releases')
    try:
        for wait_time in update_historic_releases(
            version_tags_iter, github_token, clear_existing
        ):
            for _ in tqdm(range(wait_time), desc='Waiting for rate limit'):
                sleep(1)
    except KeyboardInterrupt:
        pass

def parse_args_and_env():
    parser = ArgumentParser()
    parser.add_argument('brave_core_path', type=str)
    parser.add_argument('--clear-existing', action='store_true')
    args = parser.parse_args()
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print('GITHUB_TOKEN is not set')
        sys.exit(1)
    return args.brave_core_path, github_token, args.clear_existing

def get_tags_most_recent_first(brave_core_path):
    output = check_output(['git', 'tag', '-l'], cwd=brave_core_path, text=True)
    return reversed(output.splitlines())

def extract_version_tags(tags):
    result = []
    for tag in tags:
        try:
            extract_version(tag)
        except ValueError:
            pass
        else:
            result.append(tag)
    return result

if __name__ == '__main__':
    main()
