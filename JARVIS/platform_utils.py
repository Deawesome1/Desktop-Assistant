"""
platform_utils.py — Cross-platform helpers for JARVIS.
Import from here instead of using sys.platform checks scattered across commands.
"""

import os
import sys
import subprocess
import platform

# Ensure JARVIS root is always on path when this module is imported
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Register this module under JARVIS.platform_utils as well so that
# "from JARVIS.platform_utils import ..." works without changing any files.
import types as _types
_jarvis_pkg = sys.modules.get("JARVIS")
if _jarvis_pkg is None:
    _jarvis_pkg = _types.ModuleType("JARVIS")
    _jarvis_pkg.__path__ = [_ROOT]
    _jarvis_pkg.__package__ = "JARVIS"
    sys.modules["JARVIS"] = _jarvis_pkg
sys.modules["JARVIS.platform_utils"] = sys.modules[__name__]

IS_WINDOWS = sys.platform == "win32"
IS_MAC     = sys.platform == "darwin"
IS_LINUX   = sys.platform.startswith("linux")
OS_NAME    = platform.system()


def get_desktop() -> str:
    home = os.path.expanduser("~")
    candidates = []
    if IS_WINDOWS:
        candidates = [
            os.path.join(home, "OneDrive", "Desktop"),
            os.path.join(home, "Desktop"),
        ]
    elif IS_MAC:
        candidates = [os.path.join(home, "Desktop")]
    else:
        candidates = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "desktop"),
        ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    fallback = os.path.join(home, "Desktop")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def get_home() -> str:
    return os.path.expanduser("~")


def get_downloads() -> str:
    return os.path.join(os.path.expanduser("~"), "Downloads")


def open_file(path: str) -> bool:
    try:
        if IS_WINDOWS:
            os.startfile(path)
        elif IS_MAC:
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception as e:
        print(f"[platform_utils] open_file failed: {e}")
        return False


def open_url(url: str) -> bool:
    import webbrowser
    webbrowser.open(url)
    return True


def launch_app(path_or_command: str) -> bool:
    try:
        if IS_WINDOWS:
            try:
                os.startfile(path_or_command)
                return True
            except Exception:
                pass
        subprocess.Popen(path_or_command, shell=True)
        return True
    except Exception as e:
        print(f"[platform_utils] launch_app failed: {e}")
        return False


def shutdown(delay_seconds: int = 10) -> bool:
    try:
        if IS_WINDOWS:
            subprocess.run(["shutdown", "/s", "/t", str(delay_seconds)])
        elif IS_MAC:
            subprocess.run(["sudo", "shutdown", "-h", f"+{delay_seconds // 60}"])
        else:
            subprocess.run(["shutdown", "-h", f"+{delay_seconds // 60}"])
        return True
    except Exception:
        return False


def restart(delay_seconds: int = 10) -> bool:
    try:
        if IS_WINDOWS:
            subprocess.run(["shutdown", "/r", "/t", str(delay_seconds)])
        elif IS_MAC:
            subprocess.run(["sudo", "shutdown", "-r", f"+{delay_seconds // 60}"])
        else:
            subprocess.run(["shutdown", "-r", f"+{delay_seconds // 60}"])
        return True
    except Exception:
        return False


def sleep_system() -> bool:
    try:
        if IS_WINDOWS:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        elif IS_MAC:
            subprocess.run(["pmset", "sleepnow"])
        else:
            subprocess.run(["systemctl", "suspend"])
        return True
    except Exception:
        return False


def lock_screen() -> bool:
    try:
        if IS_WINDOWS:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        elif IS_MAC:
            subprocess.run(["osascript", "-e",
                'tell application "System Events" to keystroke "q" '
                'using {command down, control down}'])
        else:
            for cmd in [["gnome-screensaver-command", "--lock"],
                        ["xdg-screensaver", "lock"],
                        ["loginctl", "lock-session"]]:
                try:
                    subprocess.run(cmd)
                    return True
                except FileNotFoundError:
                    continue
        return True
    except Exception:
        return False


def empty_trash() -> bool:
    try:
        if IS_WINDOWS:
            import ctypes
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 1 | 2 | 4)
        elif IS_MAC:
            subprocess.run(["osascript", "-e",
                            'tell application "Finder" to empty trash'])
        else:
            trash_dir = os.path.join(os.path.expanduser("~"), ".local/share/Trash/files")
            if os.path.isdir(trash_dir):
                import shutil
                shutil.rmtree(trash_dir)
                os.makedirs(trash_dir)
            else:
                subprocess.run(["gio", "trash", "--empty"])
        return True
    except Exception:
        return False


def set_volume(level_0_to_100: int) -> bool:
    try:
        if IS_WINDOWS:
            _windows_volume(level_0_to_100)
        elif IS_MAC:
            subprocess.run(["osascript", "-e",
                            f"set volume output volume {level_0_to_100}"])
        else:
            try:
                subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@",
                                f"{level_0_to_100}%"])
            except FileNotFoundError:
                subprocess.run(["amixer", "sset", "Master", f"{level_0_to_100}%"])
        return True
    except Exception:
        return False


def get_volume() -> int | None:
    try:
        if IS_WINDOWS:
            return _windows_get_volume()
        elif IS_MAC:
            r = subprocess.run(
                ["osascript", "-e", "output volume of (get volume settings)"],
                capture_output=True, text=True)
            return int(r.stdout.strip())
        else:
            try:
                r = subprocess.run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                                   capture_output=True, text=True)
                import re
                m = re.search(r"(\d+)%", r.stdout)
                return int(m.group(1)) if m else None
            except FileNotFoundError:
                r = subprocess.run(["amixer", "sget", "Master"],
                                   capture_output=True, text=True)
                import re
                m = re.search(r"\[(\d+)%\]", r.stdout)
                return int(m.group(1)) if m else None
    except Exception:
        return None


def mute(muted: bool = True) -> bool:
    try:
        if IS_WINDOWS:
            _windows_mute(muted)
        elif IS_MAC:
            val = "true" if muted else "false"
            subprocess.run(["osascript", "-e", f"set volume output muted {val}"])
        else:
            state = "1" if muted else "0"
            try:
                subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", state])
            except FileNotFoundError:
                toggle = "mute" if muted else "unmute"
                subprocess.run(["amixer", "sset", "Master", toggle])
        return True
    except Exception:
        return False


def _windows_volume(level: int):
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
    except Exception:
        steps_down = 50
        steps_up   = level // 2
        script = (
            f"$s = New-Object -ComObject WScript.Shell; "
            f"1..{steps_down} | % {{ $s.SendKeys([char]174) }}; "
            f"1..{steps_up}   | % {{ $s.SendKeys([char]175) }}"
        )
        subprocess.run(["powershell", "-Command", script], capture_output=True)


def _windows_get_volume() -> int | None:
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return int(volume.GetMasterVolumeLevelScalar() * 100)
    except Exception:
        return None


def _windows_mute(muted: bool):
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMute(1 if muted else 0, None)
    except Exception:
        subprocess.run(["powershell", "-Command",
                       "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"],
                      capture_output=True)


def get_clipboard() -> str | None:
    try:
        if IS_WINDOWS or IS_MAC:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            content = root.clipboard_get()
            root.destroy()
            return content.strip() or None
        else:
            try:
                r = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                   capture_output=True, text=True)
                return r.stdout.strip() or None
            except FileNotFoundError:
                r = subprocess.run(["xsel", "--clipboard", "--output"],
                                   capture_output=True, text=True)
                return r.stdout.strip() or None
    except Exception:
        return None


def clear_clipboard() -> bool:
    try:
        if IS_WINDOWS:
            subprocess.run("echo.|clip", shell=True)
        elif IS_MAC:
            subprocess.run(["pbcopy"], input=b"")
        else:
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=b"")
            except FileNotFoundError:
                subprocess.run(["xsel", "--clipboard", "--clear"])
        return True
    except Exception:
        return False


def take_screenshot(filepath: str) -> bool:
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(filepath)
        return True
    except ImportError:
        try:
            if IS_MAC:
                subprocess.run(["screencapture", filepath])
                return True
            elif IS_LINUX:
                subprocess.run(["scrot", filepath])
                return True
        except Exception:
            pass
        return False
    except Exception:
        return False


def get_wifi_info() -> dict | None:
    try:
        import re
        if IS_WINDOWS:
            r = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                               capture_output=True, text=True)
            out = r.stdout
            ssid   = re.search(r"SSID\s*:\s*(.+)",      out)
            signal = re.search(r"Signal\s*:\s*(\d+)%",  out)
            speed  = re.search(r"Receive rate.*?:\s*([\d\.]+)", out)
            if not ssid:
                return None
            return {
                "ssid":   ssid.group(1).strip(),
                "signal": int(signal.group(1)) if signal else None,
                "speed":  float(speed.group(1)) if speed else None,
            }
        elif IS_MAC:
            r = subprocess.run(
                ["/System/Library/PrivateFrameworks/Apple80211.framework"
                 "/Versions/Current/Resources/airport", "-I"],
                capture_output=True, text=True)
            out   = r.stdout
            ssid  = re.search(r"SSID:\s*(.+)",        out)
            rssi  = re.search(r"agrCtlRSSI:\s*(-?\d+)", out)
            if not ssid:
                return None
            rssi_val = int(rssi.group(1)) if rssi else -80
            pct = max(0, min(100, 2 * (rssi_val + 100)))
            return {"ssid": ssid.group(1).strip(), "signal": pct, "speed": None}
        else:
            r = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
            ssid = r.stdout.strip()
            if not ssid:
                return None
            return {"ssid": ssid, "signal": None, "speed": None}
    except Exception:
        return None