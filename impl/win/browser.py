from ctypes import byref, c_uint, c_void_p, create_string_buffer, string_at
from impl.browser import Browser
from os.path import exists, join
from struct import unpack

import ctypes
import os


class WindowsBrowser(Browser):

    SUPPORTED_ARCHITECTURES = ('x64', 'x86', 'arm64')

    app_name_prefix = None

    @property
    def is_installed(self):
        return self.brave_exe is not None

    @property
    def version(self):
        brave_exe = self.brave_exe
        if brave_exe is None:
            return None
        return _get_file_version(brave_exe)

    @property
    def profile_paths(self):
        brave_software_dir = join(os.environ['LOCALAPPDATA'], 'BraveSoftware')
        return [join(brave_software_dir, self.app_name, 'User Data')]

    def launch(self):
        os.startfile(self.brave_exe)

    @property
    def app_name(self):
        if self.channel == 'release':
            return self.app_name_prefix
        return f'{self.app_name_prefix}-{self.channel.title()}'

    @property
    def brave_exe(self):
        brave_software_dir = \
            _get_brave_software_dir(self.architecture, self.scope)
        result = \
            join(brave_software_dir, self.app_name, 'Application', 'brave.exe')
        if not exists(result):
            return None
        # Program Files holds both x64 and arm64 builds:
        if _get_architecture(result) != self.architecture:
            return None
        return result


class Brave(WindowsBrowser):
    app_name_prefix = 'Brave-Browser'
    product_title = 'Brave'


class Origin(WindowsBrowser):
    app_name_prefix = 'Brave-Origin'
    product_title = 'Origin'


def _get_brave_software_dir(architecture, scope):
    if scope == 'user':
        env_var = 'LOCALAPPDATA'
    elif architecture == 'x86':
        env_var = 'PROGRAMFILES(X86)'
    else:
        env_var = 'PROGRAMFILES'
    return join(os.environ[env_var], 'BraveSoftware')


def _get_architecture(executable_path):
    with open(executable_path, 'rb') as f:
        f.seek(0x3c)
        pe_header_offset = int.from_bytes(f.read(4), 'little')
        f.seek(pe_header_offset)
        signature = f.read(4)
        machine = int.from_bytes(f.read(2), 'little')
    if signature != b'PE\0\0':
        raise ValueError(f'Unknown executable format: {executable_path}')
    return {0x8664: 'x64', 0x014c: 'x86', 0xaa64: 'arm64'}[machine]


def _get_file_version(executable_path):
    version_dll = ctypes.windll.version
    size = version_dll.GetFileVersionInfoSizeW(executable_path, None)
    if not size:
        raise ctypes.WinError()
    data = create_string_buffer(size)
    version_dll.GetFileVersionInfoW(executable_path, 0, size, data)
    info = c_void_p()
    version_dll.VerQueryValueW(data, '\\', byref(info), byref(c_uint()))
    # dwFileVersionMS and dwFileVersionLS are at offset 8 of VS_FIXEDFILEINFO:
    ms, ls = unpack('II', string_at(info.value + 8, 8))
    return f'{ms >> 16}.{ms & 0xffff}.{ls >> 16}.{ls & 0xffff}'
