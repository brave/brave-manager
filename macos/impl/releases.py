from collections import defaultdict
from math import ceil
from os.path import exists, join, dirname, basename
from time import time
from impl import cache
from impl.util import extract_version
from zipfile import ZipFile, ZIP_DEFLATED

import json
import requests
import sys

# Github's API only gives us the latest 1000 releases. We remember older
# releases in this compressed JSON file. It can be updated with
# update_historic_releases(...) below. A CLI to this function is in
# `update_historic_releases.py`.
HISTORIC_RELEASES = join(dirname(__file__), 'historic-releases.zip')

def get_releases(channel, public_only):
    result = []
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
            result.append({
                'version': version,
                'name': release['name'].rstrip(),
                'dmgs': dmgs_this_version
            })
    return result

def group_by_minor_version(releases):
    result = defaultdict(list)
    for release in releases:
        minor_version = release['version'].rsplit('.', 1)[0]
        result[f'{minor_version}.x'].append(release)
    return result

def update_historic_releases(tags, github_token, clear_existing=False):
    zipped_json = ZippedJson(HISTORIC_RELEASES)
    if clear_existing:
        zipped_json.write({})
    historic_releases = zipped_json.read()
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
            release = response.json()
            cache_id = _get_cache_id(release)
            historic_releases[cache_id] = _trim_github_release(release)
    finally:
        zipped_json.write(historic_releases)

def _cache_releases():
    cache_path = cache.prepare('releases.json')
    if not exists(cache_path):
        historic_releases = ZippedJson(HISTORIC_RELEASES).read()
        with open(cache_path, 'w') as f:
            json.dump(historic_releases, f)
    with open(cache_path) as f:
        cached_releases = json.load(f)
    yield from cached_releases.values()
    return
    new_items = {}
    rest_is_in_cache = False
    try:
        for page_results in _paginate_releases():
            for release in page_results:
                cache_id = _get_cache_id(release)
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

def _get_cache_id(release):
    # Need str(...) because we want to use cache_id as a key in JSON, where keys
    # must be strings.
    return str(release['id'])

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
        if page == 11 and response.status_code == 422:
            raise RuntimeError(
                f'The GitHub API only returns 1000 releases but more were '
                f'requested. This indicates that {HISTORIC_RELEASES} is out of '
                f'date. Please update brave-manager or run '
                f'`python update_historic_releases.py` in its installation '
                f'directory.'
            )
        response.raise_for_status()
        yield response.json()

class ZippedJson:

    def __init__(self, zip_path):
        self.zip_path = zip_path

    def read(self):
        with self._open_zip('r') as zf:
            with zf.open(self._get_json_name_in_zip()) as f:
                return json.load(f)

    def write(self, data):
        with self._open_zip('w', compression=ZIP_DEFLATED) as zf:
            zf.writestr(self._get_json_name_in_zip(), json.dumps(data))

    def _open_zip(self, *args, **kwargs):
        return ZipFile(self.zip_path, *args, **kwargs)

    def _get_json_name_in_zip(self):
        return basename(self.zip_path).replace('.zip', '.json')
