from os.path import dirname
from subprocess import run

import importlib
import sys

def sudo(fn, *args):
    fn_qualified_name = f'{fn.__module__}.{fn.__name__}'
    run([
        'sudo', sys.executable, __file__, fn_qualified_name, *args
    ])

if __name__ == '__main__':
    fn_qualified_name = sys.argv[1]
    args = sys.argv[2:]
    module_name, fn_name = fn_qualified_name.rsplit('.', 1)
    sys.path.append(dirname(dirname(__file__)))
    module = importlib.import_module(module_name)
    fn = getattr(module, fn_name)
    fn(*args)
