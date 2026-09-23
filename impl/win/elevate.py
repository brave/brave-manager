from ctypes import Structure, byref, c_int, c_void_p, sizeof, windll, WinError
from ctypes.wintypes import DWORD, HANDLE, HINSTANCE, HKEY, HWND, LPCWSTR, \
    ULONG
from subprocess import list2cmdline

SEE_MASK_NOCLOSEPROCESS = 0x40
SW_HIDE = 0
INFINITE = 0xFFFFFFFF

class SHELLEXECUTEINFOW(Structure):
    _fields_ = [
        ('cbSize', DWORD), ('fMask', ULONG), ('hwnd', HWND),
        ('lpVerb', LPCWSTR), ('lpFile', LPCWSTR), ('lpParameters', LPCWSTR),
        ('lpDirectory', LPCWSTR), ('nShow', c_int), ('hInstApp', HINSTANCE),
        ('lpIDList', c_void_p), ('lpClass', LPCWSTR), ('hkeyClass', HKEY),
        ('dwHotKey', DWORD), ('hIcon', HANDLE), ('hProcess', HANDLE)
    ]

def run_elevated(command, cwd=None):
    # Uses ShellExecuteEx with the 'runas' verb, which shows a UAC prompt.
    info = SHELLEXECUTEINFOW()
    info.cbSize = sizeof(info)
    info.fMask = SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = 'runas'
    info.lpFile = command[0]
    info.lpParameters = list2cmdline(command[1:])
    info.lpDirectory = cwd
    info.nShow = SW_HIDE
    if not windll.shell32.ShellExecuteExW(byref(info)):
        raise WinError()
    windll.kernel32.WaitForSingleObject(info.hProcess, INFINITE)
    exit_code = DWORD()
    windll.kernel32.GetExitCodeProcess(info.hProcess, byref(exit_code))
    windll.kernel32.CloseHandle(info.hProcess)
    if exit_code.value:
        raise RuntimeError(
            f'{list2cmdline(command)} failed with exit code {exit_code.value}'
        )
