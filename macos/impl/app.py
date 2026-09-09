from os import remove
from os.path import exists, isdir
from shutil import rmtree


class App:

    product_title = None
    channels = ()

    def __init__(self, channel):
        self.channel = channel

    @property
    def is_installed(self):
        raise NotImplementedError()

    @property
    def version(self):
        raise NotImplementedError()

    @property
    def profile_paths(self):
        raise NotImplementedError()

    @property
    def has_profile(self):
        return any(exists(p) for p in self.profile_paths)

    def uninstall(self):
        raise NotImplementedError()

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
