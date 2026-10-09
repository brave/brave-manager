from win32com.client import Dispatch

import pywintypes
import win32api
import win32con
import win32security

# HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND):
_NOT_FOUND = -2147024894
_TASK_ENUM_HIDDEN = 1


def list_folder(path):
    """
    Returns the tasks and subfolders of the given task folder, or None if it
    does not exist. Each task is a (path, is_current_user) pair, where
    is_current_user says whether the task runs as the current user. Only
    includes the tasks that the current user can see.
    """
    try:
        folder = _connect().GetFolder(path)
    except pywintypes.com_error as e:
        if _get_hresult(e) == _NOT_FOUND:
            return None
        raise
    current_user = _get_current_user_sid()
    tasks = [
        (task.Path, _get_sid(task.Definition.Principal.UserId) == current_user)
        for task in folder.GetTasks(_TASK_ENUM_HIDDEN)
    ]
    folders = [subfolder.Path for subfolder in folder.GetFolders(0)]
    return tasks, folders


def delete_task(path):
    parent, name = _split(path)
    _connect().GetFolder(parent).DeleteTask(name, 0)


def delete_folder(path):
    """Fails if the folder is not empty."""
    parent, name = _split(path)
    _connect().GetFolder(parent).DeleteFolder(name, 0)


def _connect():
    service = Dispatch('Schedule.Service')
    service.Connect()
    return service


def _split(path):
    # Eg. \A\B into \A and B, and \A into \ and A:
    parent, _, name = path.rpartition('\\')
    return parent or '\\', name


def _get_sid(user):
    # A user name such as "micha", or a SID such as "S-1-5-18":
    try:
        if user.startswith('S-1-'):
            return win32security.ConvertStringSidToSid(user)
        return win32security.LookupAccountName(None, user)[0]
    except pywintypes.error:
        return None


def _get_current_user_sid():
    token = win32security.OpenProcessToken(
        win32api.GetCurrentProcess(), win32con.TOKEN_QUERY
    )
    return win32security.GetTokenInformation(token, win32security.TokenUser)[0]


def _get_hresult(com_error):
    # Errors of the Task Scheduler's methods arrive wrapped in
    # DISP_E_EXCEPTION, with the actual HRESULT in excepinfo:
    excepinfo = com_error.excepinfo
    return excepinfo[5] if excepinfo else com_error.hresult
