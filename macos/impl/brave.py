from os import remove
from os.path import exists, isdir, join, expanduser
from plistlib import load
from shutil import rmtree
from subprocess import run


class App:

    brand = None
    product_title = None
    channels = ()
    bundle_id_suffix = None

    def __init__(self, channel):
        self.channel = channel

    @property
    def dir(self):
        return join('/Applications', f'{self._bundle_name}.app')

    @property
    def is_installed(self):
        return exists(self.dir)

    @property
    def version(self):
        info_plist_path = join(self.dir, 'Contents', 'Info.plist')
        try:
            with open(info_plist_path, 'rb') as f:
                plist = load(f)
        except FileNotFoundError:
            return None
        return plist['CFBundleShortVersionString'].split('.', 1)[1]

    @property
    def profile_paths(self):
        d = self._bundle_name_dashed
        s = self.bundle_id_suffix + \
            ('' if self.channel == 'release' else f'.{self.channel}')
        return [expanduser(f'~/Library/{p}') for p in (
            f'Application Support/BraveSoftware/{d}',
            f'Caches/BraveSoftware/{d}',
            f'Saved Application State/com.brave.Browser{s}.savedState',
            f'Caches/com.brave.Browser{s}',
            f'Preferences/com.brave.Browser{s}.plist',
        )]

    @property
    def has_profile(self):
        return any(exists(p) for p in self.profile_paths)

    def uninstall(self):
        rmtree(self.dir)

    def launch(self):
        run(['open', '-a', self.dir])

    def delete_profile(self):
        for path in self.profile_paths:
            if isdir(path):
                rmtree(path)
            elif exists(path):
                remove(path)

    def accepts_installer(self, name):
        if not (name.endswith('.dmg') or name.endswith('.pkg')):
            return False
        return name.startswith(self._bundle_name_dashed)

    @property
    def _bundle_name(self):
        if self.channel == 'release':
            return self.brand
        return f'{self.brand} {self.channel.title()}'

    @property
    def _bundle_name_dashed(self):
        return self._bundle_name.replace(' ', '-')

    def __str__(self):
        if self.channel == 'release':
            return self.product_title
        return f'{self.product_title} {self.channel.title()}'

    def __repr__(self):
        return f'{type(self).__name__}({self.channel!r})'

    def __eq__(self, other):
        return type(self) is type(other) and self.channel == other.channel

    def __hash__(self):
        return hash((type(self), self.channel))


class Brave(App):
    brand = 'Brave Browser'
    product_title = 'Brave'
    channels = ('nightly', 'beta', 'release')
    bundle_id_suffix = ''


class Origin(App):
    brand = 'Brave Origin'
    product_title = 'Origin'
    channels = ('nightly', 'beta')
    bundle_id_suffix = '.origin'


PRODUCTS = {product.product_title: product for product in (Brave, Origin)}


def get_all_apps():
    for product in PRODUCTS.values():
        for channel in product.channels:
            yield product(channel)


def get_apps_with_profiles():
    return [app for app in get_all_apps() if app.has_profile]
