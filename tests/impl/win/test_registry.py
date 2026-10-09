from impl.win.registry import (
    read_value, key_exists, list_subkeys, list_values, delete_key,
    delete_value
)
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
    def test_key_exists(self):
        self.assertTrue(key_exists(HKEY_CURRENT_USER, KEY + r'\child'))
        self.assertFalse(key_exists(HKEY_CURRENT_USER, KEY + r'\x'))
    def test_list_subkeys(self):
        self.assertEqual(['child'], list_subkeys(HKEY_CURRENT_USER, KEY))
        self.assertEqual(
            [], list_subkeys(HKEY_CURRENT_USER, KEY + r'\child\grandchild')
        )
        with self.assertRaises(FileNotFoundError):
            list_subkeys(HKEY_CURRENT_USER, KEY + r'\x')
    def test_list_values(self):
        key = KEY + r'\child\grandchild'
        self.assertEqual(['name'], list_values(HKEY_CURRENT_USER, key))
        self.assertEqual([], list_values(HKEY_CURRENT_USER, KEY))
        with self.assertRaises(FileNotFoundError):
            list_values(HKEY_CURRENT_USER, KEY + r'\x')
    def test_delete_key(self):
        delete_key(HKEY_CURRENT_USER, KEY)
        with self.assertRaises(FileNotFoundError):
            OpenKey(HKEY_CURRENT_USER, KEY)
        # Deleting a non-existent key is a no-op:
        delete_key(HKEY_CURRENT_USER, KEY)
    def test_delete_value(self):
        key = KEY + r'\child\grandchild'
        delete_value(HKEY_CURRENT_USER, key, 'name')
        with self.assertRaises(FileNotFoundError):
            read_value(HKEY_CURRENT_USER, key, 'name')
        # Deleting a non-existent value or key is a no-op:
        delete_value(HKEY_CURRENT_USER, key, 'name')
        delete_value(HKEY_CURRENT_USER, KEY + r'\x', 'name')
