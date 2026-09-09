from os.path import dirname

import sys

def load_tests(loader, tests, pattern):
    # The modules in this package only import on Windows.
    if sys.platform == 'win32':
        tests.addTests(loader.discover(dirname(__file__), pattern))
    return tests
