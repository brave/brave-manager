from winreg import (
    OpenKey, EnumKey, DeleteKey, DeleteValue, QueryValueEx, KEY_SET_VALUE
)

def read_value(root, key, name):
    with OpenKey(root, key) as handle:
        return QueryValueEx(handle, name)[0]

def list_subkeys(root, key):
    result = []
    with OpenKey(root, key) as handle:
        while True:
            try:
                result.append(EnumKey(handle, len(result)))
            except OSError:
                return result

def delete_key(root, key):
    try:
        handle = OpenKey(root, key)
    except FileNotFoundError:
        return
    with handle:
        while True:
            try:
                subkey = EnumKey(handle, 0)
            except OSError:
                break
            delete_key(handle, subkey)
    DeleteKey(root, key)

def delete_value(root, key, name):
    try:
        handle = OpenKey(root, key, 0, KEY_SET_VALUE)
    except FileNotFoundError:
        return
    with handle:
        try:
            DeleteValue(handle, name)
        except FileNotFoundError:
            pass
