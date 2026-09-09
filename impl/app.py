class App:

    @property
    def is_installed(self):
        raise NotImplementedError()

    @property
    def version(self):
        raise NotImplementedError()

    def uninstall(self):
        raise NotImplementedError()
