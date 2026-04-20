import platform

def get_os_key():
    name = platform.system().lower()
    if "windows" in name:
        return "windows"
    if "darwin" in name or "mac" in name:
        return "macintosh"
    return "linux"

current_os = get_os_key()
