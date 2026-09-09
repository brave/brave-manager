class App:

    SUPPORTED_ARCHITECTURES = ('x64', 'arm64')
    SUPPORTED_SCOPES = ('user', 'system')

    def __init__(self, architecture, scope):
        self.architecture = architecture
        self.scope = scope

    @property
    def is_installed(self):
        raise NotImplementedError()

    @property
    def version(self):
        raise NotImplementedError()

    def uninstall(self):
        raise NotImplementedError()
