from impl import brave, cache, updater
from impl.sudo import sudo
from impl.util import install_dmg, install_pkg, print_done, FileDownloader
from os.path import exists, basename
from tqdm import tqdm

class Uninstall:
    def __init__(self, channel):
        self.channel = channel
    def __str__(self):
        return f'Uninstall {self.channel.title()}'
    def __call__(self):
        with print_done(f'Uninstalling {self.channel.title()}'):
            try:
                brave.uninstall(self.channel)
            except PermissionError:
                sudo(brave.uninstall, self.channel)

class Install:
    def __init__(self, channel, version, installer_url):
        self.channel = channel
        self.version = version
        self.installer_url = installer_url
    def __str__(self):
        return f'Install {basename(self.installer_url)} {self.version}'
    def __call__(self):
        cache_path = cache.prepare(self.installer_url.split('//', 1)[1])
        if not exists(cache_path):
            download_file(self.installer_url, cache_path)
        installer_basename = basename(self.installer_url)
        with print_done(f'Installing {installer_basename}'):
            if installer_basename.endswith('.dmg'):
                install_dmg(cache_path)
            elif installer_basename.endswith('.pkg'):
                sudo(install_pkg, cache_path)

class DeleteProfile:
    def __init__(self, channel):
        self.channel = channel
    def __str__(self):
        return f'Delete {self.channel.title()} profile'
    def __call__(self):
        with print_done(f'Deleting {self.channel.title()} profile'):
            brave.delete_profile(self.channel)

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
        if self.scope == 'system':
            sudo(updater.uninstall, self.scope)
        else:
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
