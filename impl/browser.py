from dataclasses import dataclass
from impl.app import App
from os import remove
from os.path import exists, isdir
from shutil import rmtree


@dataclass(frozen=True)
class Browser(App):

    CHANNELS = ('nightly', 'dev', 'beta', 'release')
    # Brave stopped publishing Dev releases in November 2023:
    INSTALLABLE_CHANNELS = ('nightly', 'beta', 'release')
    SUPPORTED_ARCHITECTURES = ('x64', 'arm64')

    architecture: str
    channel: str

    @classmethod
    def get_apps(cls):
        for channel in cls.CHANNELS:
            for architecture in cls.SUPPORTED_ARCHITECTURES:
                for is_system_level in (False, True):
                    yield cls(is_system_level, architecture, channel)

    @property
    def name(self):
        return self._with_details(self.channel.title())

    @property
    def profile_paths(self):
        raise NotImplementedError()

    @property
    def has_profile(self):
        return any(exists(p) for p in self.profile_paths)

    def launch(self):
        raise NotImplementedError()

    def delete_profile(self):
        for path in self.profile_paths:
            if isdir(path):
                rmtree(path)
            elif exists(path):
                remove(path)

    def accepts_installer(self, name):
        raise NotImplementedError()

    def create_install_action(self, version, installer_url):
        raise NotImplementedError()

    @property
    def _details(self):
        return [self.architecture] + super()._details

    @property
    def title(self):
        if self.channel == 'release':
            return self.product_title
        return f'{self.product_title} {self.channel.title()}'

    def __str__(self):
        return self._with_details(self.title)
