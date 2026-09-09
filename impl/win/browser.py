from ctypes import byref, c_uint, c_void_p, create_string_buffer, string_at
from impl.browser import Browser
from impl.elevate import elevate
from impl.win import registry
from os.path import exists, join, dirname
from shutil import rmtree
from struct import unpack
from subprocess import run
from winreg import HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE

import ctypes
import os

APP_GUIDS = {
    'Brave-Browser-Nightly': '{C6CB981E-DB30-4876-8639-109F8933582C}',
    'Brave-Browser-Dev': '{CB2150F2-595F-4633-891A-E39720CE0531}',
    'Brave-Browser-Beta': '{103BD053-949B-43A8-9120-2E424887DE11}',
    'Brave-Browser': '{AFE6A462-C574-4B8A-AF43-4CC60DF4563B}',
    'Brave-Origin-Nightly': '{50474E96-9CD2-4BC8-B0A7-0D4B6EF2E709}',
    'Brave-Origin-Dev': '{716D6A4A-D071-47A8-AC64-DBDE3EE3797B}',
    'Brave-Origin-Beta': '{56DA94FD-D872-416B-BFC4-1D7011DA7473}',
    'Brave-Origin': '{F1EF32DE-F987-4289-81D2-6C4780027F9B}'
}


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

    def uninstall(self):
        args = (self.app_name, self.scope, dirname(self.brave_exe))
        if self.scope == 'system':
            elevate(_uninstall, *args)
        else:
            _uninstall(*args)

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


def _uninstall(app_name, scope, install_dir):
    # Brave's registry keys live in the 32-bit view. Under HKLM, that's
    # WOW6432Node. HKCU has no such redirection.
    if scope == 'user':
        root, prefix = HKEY_CURRENT_USER, 'SOFTWARE'
    else:
        root, prefix = HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node'
    uninstall_key = rf'{prefix}\Microsoft\Windows\CurrentVersion\Uninstall' \
        rf'\BraveSoftware {app_name}'
    try:
        uninstall_string = \
            registry.read_value(root, uninstall_key, 'UninstallString')
    except FileNotFoundError:
        pass
    else:
        cp = run(f'{uninstall_string} --force-uninstall')
        if cp.returncode not in (0, 19):
            cp.check_returncode()
    registry.delete_key(root, uninstall_key)
    if exists(install_dir):
        rmtree(install_dir)
    guid = APP_GUIDS[app_name]
    registry.delete_key(root, rf'{prefix}\BraveSoftware\Update\Clients\{guid}')


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
