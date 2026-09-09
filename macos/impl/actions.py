from impl import cache, updater
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
            self.app.uninstall()

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
        with print_done(f'Installing {basename(self.installer_url)}'):
            self._run_installer(cache_path)
    def _run_installer(self, path):
        raise NotImplementedError()

class InstallDmg(Install):
    def _run_installer(self, path):
        install_dmg(path)

class InstallPkg(Install):
    def _run_installer(self, path):
        sudo(install_pkg, path)

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
