from impl.app import App
from os import remove
from os.path import exists, isdir
from shutil import rmtree


class Browser(App):

    product_title = None
    channels = ()

    def __init__(self, channel, scope):
        super().__init__(scope)
        self.channel = channel

    @classmethod
    def get_apps(cls):
        for channel in cls.channels:
            for scope in cls.SUPPORTED_SCOPES:
                yield cls(channel, scope)

    @property
    def name(self):
        return self._with_scope(self.channel.title())

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

    def _with_scope(self, text):
        if len(self.SUPPORTED_SCOPES) == 1:
            return text
        return f'{text} ({self.scope})'

    def __str__(self):
        if self.channel == 'release':
            result = self.product_title
        else:
            result = f'{self.product_title} {self.channel.title()}'
        return self._with_scope(result)

    def __repr__(self):
        return f'{type(self).__name__}({self.channel!r}, {self.scope!r})'

    def __eq__(self, other):
        return type(self) is type(other) and self.channel == other.channel \
            and self.scope == other.scope

    def __hash__(self):
        return hash((type(self), self.channel, self.scope))
