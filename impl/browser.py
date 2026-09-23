from dataclasses import dataclass
from impl.app import App
from os import remove, walk, chmod
from os.path import exists, isdir, join
from shutil import rmtree
from stat import S_IWRITE


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
                _rmtree(path)
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


def _rmtree(path):
    try:
        rmtree(path)
    except PermissionError:
        # Windows refuses to delete read-only files. Profiles contain some:
        for parent_dir, _, file_names in walk(path):
            for file_name in file_names:
                chmod(join(parent_dir, file_name), S_IWRITE)
        rmtree(path)
