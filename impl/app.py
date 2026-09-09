class App:

    SUPPORTED_SCOPES = ('user', 'system')

    def __init__(self, scope):
        self.scope = scope

    @property
    def is_installed(self):
        raise NotImplementedError()

    @property
    def version(self):
        raise NotImplementedError()

    def uninstall(self):
        raise NotImplementedError()
