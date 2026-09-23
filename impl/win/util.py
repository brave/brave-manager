from ctypes import byref, c_uint, c_void_p, create_string_buffer, string_at
from struct import unpack

import ctypes


def get_architecture(executable_path):
    with open(executable_path, 'rb') as f:
        f.seek(0x3c)
        pe_header_offset = int.from_bytes(f.read(4), 'little')
        f.seek(pe_header_offset)
        signature = f.read(4)
        machine = int.from_bytes(f.read(2), 'little')
    if signature != b'PE\0\0':
        raise ValueError(f'Unknown executable format: {executable_path}')
    return {0x8664: 'x64', 0x014c: 'x86', 0xaa64: 'arm64'}[machine]


def get_file_version(executable_path):
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
