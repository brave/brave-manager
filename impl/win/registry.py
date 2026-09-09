from winreg import OpenKey, EnumKey, DeleteKey, QueryValueEx

def read_value(root, key, name):
    with OpenKey(root, key) as handle:
        return QueryValueEx(handle, name)[0]

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
