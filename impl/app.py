from dataclasses import dataclass


@dataclass(frozen=True)
class App:

    SUPPORTED_ARCHITECTURES = ('x64', 'arm64')

    product_title = None

    architecture: str
    is_system_level: bool

    @classmethod
    def get_apps(cls):
        for architecture in cls.SUPPORTED_ARCHITECTURES:
            for is_system_level in (False, True):
                yield cls(architecture, is_system_level)

    @property
    def is_installed(self):
        raise NotImplementedError()

    @property
    def version(self):
        raise NotImplementedError()

    def uninstall(self):
        raise NotImplementedError()

    def _with_details(self, text):
        details = []
        if len(self.SUPPORTED_ARCHITECTURES) > 1:
            details.append(self.architecture)
        details.append('system' if self.is_system_level else 'user')
        return f'{text} ({", ".join(details)})'

    def __str__(self):
        return self._with_details(self.product_title)
