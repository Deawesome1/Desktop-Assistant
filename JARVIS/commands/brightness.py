"""
commands/brightness.py — Cross-platform brightness control.
Windows desktop: WMI (laptop displays only) — most desktop monitors
  require DDC/CI hardware support or manual OSD.
Mac:   osascript display brightness.
Linux: xrandr or brightnessctl.
Triggers: "brightness up/down", "set brightness to X", "screen brightness"
"""
import re
import subprocess
import sys
from bot.speaker import speak


def _get() -> int | None:
    if sys.platform == "win32":
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness "
                 "-ErrorAction SilentlyContinue).CurrentBrightness"],
                capture_output=True, text=True, timeout=4
            )
            val = r.stdout.strip()
            return int(val) if val.isdigit() else None
        except Exception:
            return None
    elif sys.platform == "darwin":
        try:
            r = subprocess.run(
                ["osascript", "-e", "tell application \"System Events\" to "
                 "get brightness of (first desktop whose active is true)"],
                capture_output=True, text=True, timeout=4
            )
            return int(float(r.stdout.strip()) * 100)
        except Exception:
            return None
    else:
        try:
            r = subprocess.run(
                ["brightnessctl", "get"], capture_output=True, text=True, timeout=4
            )
            max_r = subprocess.run(
                ["brightnessctl", "max"], capture_output=True, text=True, timeout=4
            )
            val = int(r.stdout.strip())
            mx  = int(max_r.stdout.strip())
            return int(val / mx * 100) if mx else None
        except Exception:
            return None


def _set(level: int) -> bool:
    level = max(0, min(100, level))
    if sys.platform == "win32":
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods "
                 f"-ErrorAction SilentlyContinue).WmiSetBrightness(1, {level})"],
                capture_output=True, timeout=4
            )
            return r.returncode == 0
        except Exception:
            return False
    elif sys.platform == "darwin":
        try:
            brightness = level / 100.0
            subprocess.run(
                ["osascript", "-e",
                 f"tell application \"System Events\" to set brightness of "
                 f"(first desktop whose active is true) to {brightness}"],
                capture_output=True, timeout=4
            )
            return True
        except Exception:
            return False
    else:
        try:
            subprocess.run(
                ["brightnessctl", "set", f"{level}%"],
                capture_output=True, timeout=4
            )
            return True
        except FileNotFoundError:
            try:
                subprocess.run(
                    ["xrandr", "--output", "eDP-1", "--brightness",
                     str(level / 100.0)],
                    capture_output=True, timeout=4
                )
                return True
            except Exception:
                return False


def run(query: str) -> str:
    q = query.lower()
    current = _get()

    match = re.search(r"(\d+)", q)
    if match and any(p in q for p in ["set brightness", "brightness to", "set it to"]):
        level = int(match.group(1))
        if _set(level):
            response = f"Brightness set to {level} percent."
        else:
            response = ("I couldn't set the brightness. On a desktop, most monitors "
                        "require adjusting brightness via their physical buttons or OSD menu.")
        speak(response)
        return response

    if any(w in q for w in ["up", "increase", "brighter", "raise"]):
        new = min(100, (current or 50) + 10)
        if _set(new):
            response = f"Brightness up to {new} percent."
        else:
            response = ("Brightness control isn't available on this monitor. "
                        "Use your monitor's physical buttons to adjust brightness.")
        speak(response)
        return response

    if any(w in q for w in ["down", "decrease", "dimmer", "lower", "dim"]):
        new = max(0, (current or 50) - 10)
        if _set(new):
            response = f"Brightness down to {new} percent."
        else:
            response = ("Brightness control isn't available on this monitor. "
                        "Use your monitor's physical buttons to adjust brightness.")
        speak(response)
        return response

    if current is not None:
        response = f"Screen brightness is at {current} percent."
    else:
        response = ("I can't read brightness on this monitor. Desktop monitors "
                    "typically require physical buttons or OSD to adjust brightness.")
    speak(response)
    return response