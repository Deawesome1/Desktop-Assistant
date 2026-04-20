# commands/os_scanner/__init__.py

import platform

def get_os_key() -> str:
    sys_name = platform.system().lower()
    if "windows" in sys_name:
        return "windows"
    if "darwin" in sys_name or "mac" in sys_name:
        return "macintosh"
    return "linux"

current_os = get_os_key()
