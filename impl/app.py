from dataclasses import dataclass


@dataclass(frozen=True)
class App:

    product_title = None

    is_system_level: bool

    @classmethod
    def get_apps(cls):
        for is_system_level in (False, True):
            yield cls(is_system_level)

    @property
    def is_installed(self):
        raise NotImplementedError()

    @property
    def version(self):
        raise NotImplementedError()

    def uninstall(self):
        raise NotImplementedError()

    def _with_details(self, text):
        return f'{text} ({", ".join(self._details)})'

    @property
    def _details(self):
        return ['system' if self.is_system_level else 'user']

    def __str__(self):
        return self._with_details(self.product_title)
