class App:

    SUPPORTED_ARCHITECTURES = ('x64', 'arm64')

    def __init__(self, architecture, is_system_level):
        self.architecture = architecture
        self.is_system_level = is_system_level

    @property
    def is_installed(self):
        raise NotImplementedError()

    @property
    def version(self):
        raise NotImplementedError()

    def uninstall(self):
        raise NotImplementedError()
