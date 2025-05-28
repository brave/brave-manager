from collections import defaultdict
from math import ceil
from os.path import exists, join, dirname
from shutil import copy
from time import time
from impl import cache
from impl.util import extract_version

import json
import requests
import sys

# Github's API only gives us the latest 1000 releases. We remember older
# releases in this JSON file. It can be updated with
# update_historic_releases(...) below. A CLI to this function is in
# `update_historic_releases.py`.
HISTORIC_RELEASES = join(dirname(__file__), 'historic-releases.json')

def get_releases(channel, public_only, max_num):
    result = {}
    for release in _cache_releases():
        if not release['name'].startswith(channel.title()):
            continue
        if public_only and release['prerelease']:
            continue
        try:
            version = extract_version(release['tag_name'])
        except ValueError:
            continue
        dmgs_this_version = {
            asset['name']: asset['browser_download_url']
            for asset in release['assets'] if asset['name'].endswith('.dmg')
        }
        if dmgs_this_version:
            result[version] = dmgs_this_version
            if len(result) == max_num:
                break
    return result

def group_by_minor_version(releases):
    result = defaultdict(dict)
    for version, dmgs in releases.items():
        minor_version = version.rsplit('.', 1)[0]
        minor_version_key = f'{minor_version}.x'
        result[minor_version_key][version] = dmgs
    return result

def update_historic_releases(tags, github_token):
    with open(HISTORIC_RELEASES) as f:
        historic_releases = json.load(f)
    try:
        for tag in tags:
            if tag in historic_releases:
                continue
            url = f'https://api.github.com/repos/brave/brave-browser/releases/'\
                  f'tags/{tag}'
            headers = {'Authorization': f'Bearer {github_token}'}
            response = requests.get(url, headers=headers)
            ratelimit_remaining = int(response.headers['x-ratelimit-remaining'])
            ratelimit_reset = int(response.headers['x-ratelimit-reset'])
            if response.status_code == 403 and ratelimit_remaining == 0:
                wait_time = ceil(ratelimit_reset - time())
                yield wait_time
                response = requests.get(url, headers=headers)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            historic_releases[tag] = _trim_github_release(response.json())
    finally:
        with open(HISTORIC_RELEASES, 'w') as f:
            json.dump(historic_releases, f)

def _cache_releases():
    cache_path = cache.prepare('releases.json')
    if not exists(cache_path):
        copy(HISTORIC_RELEASES, cache_path)
    with open(cache_path) as f:
        cached_releases = json.load(f)
    new_items = {}
    rest_is_in_cache = False
    try:
        for page_results in _paginate_releases():
            for release in page_results:
                # Need str(...) because we want to use cache_id as a key in
                # JSON, where keys must be strings.
                cache_id = str(release['id'])
                if cache_id in cached_releases:
                    rest_is_in_cache = True
                    break
                else:
                    release_thin = _trim_github_release(release)
                    new_items[cache_id] = release_thin
                    yield release_thin
            if rest_is_in_cache:
                break
        yield from cached_releases.values()
    except GeneratorExit:
        cached_releases.update(new_items)
        with open(cache_path, 'w') as f:
            json.dump(cached_releases, f)

def _trim_github_release(release):
    return {
        'name': release['name'],
        'tag_name': release['tag_name'],
        'prerelease': release['prerelease'],
        'assets': [
            {
                'name': asset['name'],
                'browser_download_url':
                    asset['browser_download_url']
            }
            for asset in release['assets']
        ]
    }

def _paginate_releases():
    for page in range(1, sys.maxsize):
        url = f'https://api.github.com/repos/brave/brave-browser/releases?' \
              f'per_page=100&page={page}'
        response = requests.get(url)
        response.raise_for_status()
        yield response.json()
