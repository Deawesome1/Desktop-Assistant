# Desktop_Assistant/launcher.py
from __future__ import annotations
import os
import sys
import subprocess
import shlex
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("jarvis.launcher")

def _resolve_windows_shortcut(path: str) -> str:
    """Return target of .lnk if possible, otherwise return original path."""
    try:
        if not path.lower().endswith(".lnk"):
            return path
        import pythoncom
        from win32com.shell import shell, shellcon
        shortcut = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None,
                                             pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
        persist = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
        persist.Load(path)
        # GetPath returns (path, find_data, flags)
        target, _, _ = shortcut.GetPath(shell.SLGP_UNCPRIORITY)
        return target or path
    except Exception:
        logger.exception("Failed to resolve .lnk %s", path)
        return path

def _launch_windows(path: str, elevate: bool = False) -> Dict[str, Any]:
    path = _resolve_windows_shortcut(path)
    try:
        if elevate:
            # ShellExecute with "runas" to prompt for elevation
            import ctypes
            SEE_MASK_NOCLOSEPROCESS = 0x00000040
            ShellExecuteEx = ctypes.windll.shell32.ShellExecuteExW
            class SHELLEXECUTEINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_ulong),
                            ("fMask", ctypes.c_ulong),
                            ("hwnd", ctypes.c_void_p),
                            ("lpVerb", ctypes.c_wchar_p),
                            ("lpFile", ctypes.c_wchar_p),
                            ("lpParameters", ctypes.c_wchar_p),
                            ("lpDirectory", ctypes.c_wchar_p),
                            ("nShow", ctypes.c_int),
                            ("hInstApp", ctypes.c_void_p),
                            ("lpIDList", ctypes.c_void_p),
                            ("lpClass", ctypes.c_wchar_p),
                            ("hkeyClass", ctypes.c_void_p),
                            ("dwHotKey", ctypes.c_ulong),
                            ("hIcon", ctypes.c_void_p),
                            ("hProcess", ctypes.c_void_p)]
            ei = SHELLEXECUTEINFO()
            ei.cbSize = ctypes.sizeof(ei)
            ei.fMask = SEE_MASK_NOCLOSEPROCESS
            ei.hwnd = None
            ei.lpVerb = "runas"
            ei.lpFile = path
            ei.lpParameters = None
            ei.lpDirectory = None
            ei.nShow = 1
            ok = ShellExecuteEx(ctypes.byref(ei))
            return {"ok": bool(ok), "method": "shell_runas" if elevate else "startfile"}
        else:
            os.startfile(path)
            return {"ok": True, "method": "startfile"}
    except Exception:
        logger.exception("Failed to launch on Windows: %s", path)
        return {"ok": False, "error": "launch_failed"}

def _launch_mac(path: str, elevate: bool = False) -> Dict[str, Any]:
    try:
        p = Path(path)
        if p.suffix.lower() == ".app" and p.is_dir():
            cmd = ["open", str(p)]
        else:
            cmd = ["open", str(path)]
        if elevate:
            # Use AppleScript to prompt for admin (user consent required)
            ascript = f'do shell script "open {shlex.quote(str(path))}" with administrator privileges'
            subprocess.run(["osascript", "-e", ascript], check=True)
            return {"ok": True, "method": "osascript_elevate"}
        subprocess.run(cmd, check=True)
        return {"ok": True, "method": "open"}
    except Exception:
        logger.exception("Failed to launch on macOS: %s", path)
        return {"ok": False, "error": "launch_failed"}

def _launch_linux(path: str, elevate: bool = False) -> Dict[str, Any]:
    try:
        p = Path(path)
        if p.is_file() and os.access(str(p), os.X_OK):
            # executable file
            subprocess.Popen([str(p)])
            return {"ok": True, "method": "exec"}
        else:
            # open with default handler
            subprocess.run(["xdg-open", str(path)], check=True)
            return {"ok": True, "method": "xdg-open"}
    except Exception:
        logger.exception("Failed to launch on Linux: %s", path)
        return {"ok": False, "error": "launch_failed"}

def launch_app(path: str, *, requires_admin: bool = False) -> Dict[str, Any]:
    """
    Launch an app path cross-platform.
    Returns a dict with keys: ok (bool), method (str), error (optional).
    """
    if not path:
        return {"ok": False, "error": "no_path"}
    try:
        if sys.platform.startswith("win"):
            return _launch_windows(path, elevate=bool(requires_admin))
        if sys.platform.startswith("darwin"):
            return _launch_mac(path, elevate=bool(requires_admin))
        # assume linux/unix
        return _launch_linux(path, elevate=bool(requires_admin))
    except Exception:
        logger.exception("Unhandled error launching %s", path)
        return {"ok": False, "error": "unhandled_exception"}
