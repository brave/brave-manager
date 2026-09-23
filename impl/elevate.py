from os.path import dirname

import importlib
import json
import sys

if sys.platform == 'win32':
    from impl.win.elevate import run_elevated
else:
    from impl.mac.elevate import run_elevated

def elevate(fn, *args):
    fn_qualified_name = f'{fn.__module__}.{fn.__name__}'
    command = [
        sys.executable, '-m', __name__, fn_qualified_name, json.dumps(args)
    ]
    run_elevated(command, cwd=dirname(dirname(__file__)))

if __name__ == '__main__':
    fn_qualified_name, args_json = sys.argv[1:]
    module_name, fn_name = fn_qualified_name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    fn = getattr(module, fn_name)
    fn(*json.loads(args_json))
