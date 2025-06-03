from impl import brave, cache, updater
from impl.util import install_dmg, print_done, FileDownloader
from os.path import exists
from tqdm import tqdm

class Uninstall:
    def __init__(self, channel):
        self.channel = channel
    def __str__(self):
        return f'Uninstall {self.channel.title()}'
    def __call__(self):
        with print_done(f'Uninstalling {self.channel.title()}'):
            brave.uninstall(self.channel)

class Install:
    def __init__(self, channel, version, dmg_url):
        self.channel = channel
        self.version = version
        self.dmg_url = dmg_url
    def __str__(self):
        return f'Install {self.channel.title()} {self.version}'
    def __call__(self):
        cache_path = cache.prepare(self.dmg_url.split('//', 1)[1])
        if not exists(cache_path):
            download_file(self.dmg_url, cache_path)
        with print_done(f'Installing {self.channel.title()}'):
            install_dmg(cache_path)

class Launch:
    def __init__(self, channel):
        self.channel = channel
    def __str__(self):
        return f'Launch {self.channel.title()}'
    def __call__(self):
        brave.launch(self.channel)

class UninstallUpdater:
    def __init__(self, scope):
        self.scope = scope
    def __str__(self):
        return f'Uninstall Brave Updater ({self.scope})'
    def __call__(self):
        updater.uninstall(self.scope)

class ClearCache:
    def __str__(self):
        return 'Clear the cache'
    def __call__(self):
        cache.clear()

def download_file(url, path):
    print(f'Downloading {url}:')
    downloader = FileDownloader(url, path)
    total_size = downloader.start()
    progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
    for num_bytes in downloader.run():
        progress_bar.update(num_bytes)
    progress_bar.close()
