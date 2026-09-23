from impl.win.registry import read_value, list_subkeys, delete_key
from unittest import TestCase
from winreg import HKEY_CURRENT_USER, CreateKey, SetValueEx, OpenKey, \
    REG_SZ

KEY = r'SOFTWARE\brave-manager-test'

class RegistryTest(TestCase):
    def setUp(self):
        with CreateKey(HKEY_CURRENT_USER, KEY + r'\child\grandchild') as key:
            SetValueEx(key, 'name', 0, REG_SZ, 'value')
    def tearDown(self):
        delete_key(HKEY_CURRENT_USER, KEY)
    def test_read_value(self):
        key = KEY + r'\child\grandchild'
        self.assertEqual('value', read_value(HKEY_CURRENT_USER, key, 'name'))
        with self.assertRaises(FileNotFoundError):
            read_value(HKEY_CURRENT_USER, key, 'missing')
        with self.assertRaises(FileNotFoundError):
            read_value(HKEY_CURRENT_USER, KEY + r'\x', 'name')
    def test_list_subkeys(self):
        self.assertEqual(['child'], list_subkeys(HKEY_CURRENT_USER, KEY))
        self.assertEqual(
            [], list_subkeys(HKEY_CURRENT_USER, KEY + r'\child\grandchild')
        )
        with self.assertRaises(FileNotFoundError):
            list_subkeys(HKEY_CURRENT_USER, KEY + r'\x')
    def test_delete_key(self):
        delete_key(HKEY_CURRENT_USER, KEY)
        with self.assertRaises(FileNotFoundError):
            OpenKey(HKEY_CURRENT_USER, KEY)
        # Deleting a non-existent key is a no-op:
        delete_key(HKEY_CURRENT_USER, KEY)
