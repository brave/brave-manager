from impl import cache, updater
from impl.brave import PRODUCTS
from impl.sudo import sudo
from impl.util import install_dmg, install_pkg, print_done, FileDownloader
from os.path import exists, basename
from tqdm import tqdm

class Uninstall:
    def __init__(self, app):
        self.app = app
    def __str__(self):
        return f'Uninstall {self.app}'
    def __call__(self):
        with print_done(f'Uninstalling {self.app}'):
            try:
                self.app.uninstall()
            except PermissionError:
                # It would be nice to be able to call `sudo(self.app.uninstall)`
                # here. But `sudo` does not support bound methods. So we use a
                # helper function, `_uninstall_with_sudo`:
                sudo(
                    _uninstall_with_sudo, self.app.product_title,
                    self.app.channel
                )

class Install:
    def __init__(self, version, installer_url):
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
    def __init__(self, app):
        self.app = app
    def __str__(self):
        return f'Delete {self.app} profile'
    def __call__(self):
        with print_done(f'Deleting {self.app} profile'):
            self.app.delete_profile()

class Launch:
    def __init__(self, app):
        self.app = app
    def __str__(self):
        return f'Launch {self.app}'
    def __call__(self):
        self.app.launch()

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

def _uninstall_with_sudo(product_title, channel):
    app = PRODUCTS[product_title](channel)
    app.uninstall()
