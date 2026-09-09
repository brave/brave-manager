from impl.app import App
from os import remove
from os.path import exists, isdir
from shutil import rmtree


class Browser(App):

    product_title = None
    channels = ()

    def __init__(self, channel, architecture, scope):
        super().__init__(architecture, scope)
        self.channel = channel

    @classmethod
    def get_apps(cls):
        for channel in cls.channels:
            for architecture in cls.SUPPORTED_ARCHITECTURES:
                for scope in cls.SUPPORTED_SCOPES:
                    yield cls(channel, architecture, scope)

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

    def _with_details(self, text):
        details = []
        if len(self.SUPPORTED_ARCHITECTURES) > 1:
            details.append(self.architecture)
        if len(self.SUPPORTED_SCOPES) > 1:
            details.append(self.scope)
        if not details:
            return text
        return f'{text} ({", ".join(details)})'

    def __str__(self):
        if self.channel == 'release':
            result = self.product_title
        else:
            result = f'{self.product_title} {self.channel.title()}'
        return self._with_details(result)

    def __repr__(self):
        return f'{type(self).__name__}' \
            f'({self.channel!r}, {self.architecture!r}, {self.scope!r})'

    def __eq__(self, other):
        return type(self) is type(other) and self.channel == other.channel \
            and self.architecture == other.architecture \
            and self.scope == other.scope

    def __hash__(self):
        return hash(
            (type(self), self.channel, self.architecture, self.scope)
        )
