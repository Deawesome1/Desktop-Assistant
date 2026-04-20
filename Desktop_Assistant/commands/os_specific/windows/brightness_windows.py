"""
brightness_windows.py — JARVIS Command (Windows)
Adjust or read screen brightness using WMI via PowerShell.

Supports:
    - "brightness up"
    - "brightness down"
    - "set brightness to 50"
    - "screen brightness"

Note:
    Works only on internal laptop displays or monitors with WMI brightness support.
"""

import re
import subprocess
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "brightness"
COMMAND_ALIASES: List[str] = [
    "brightness", "screen brightness", "brightness up", "brightness down",
    "set brightness", "brightness to"
]
COMMAND_DESCRIPTION: str = "Adjusts or reads screen brightness on Windows using WMI."
COMMAND_OS_SUPPORT: List[str] = ["windows"]
COMMAND_CATEGORY: str = "system"
COMMAND_REQUIRES_INTERNET: bool = False
COMMAND_REQUIRES_ADMIN: bool = False


# ---------------------------------------------------------------------------
# Metadata API
# ---------------------------------------------------------------------------

def get_metadata() -> Dict[str, Any]:
    return {
        "name": COMMAND_NAME,
        "aliases": COMMAND_ALIASES,
        "description": COMMAND_DESCRIPTION,
        "os_support": COMMAND_OS_SUPPORT,
        "category": COMMAND_CATEGORY,
        "requires_internet": COMMAND_REQUIRES_INTERNET,
        "requires_admin": COMMAND_REQUIRES_ADMIN,
    }


def is_supported_on_os(os_key: str) -> bool:
    return os_key == "windows"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_brightness() -> Optional[int]:
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


def _set_brightness(level: int) -> bool:
    level = max(0, min(100, level))
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


# ---------------------------------------------------------------------------
# Public run() entrypoint
# ---------------------------------------------------------------------------

def run(
    brain: Brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    q = user_text.lower()
    current = _get_brightness()

    # Explicit numeric set
    match = re.search(r"(\d+)", q)
    if match and any(p in q for p in ["set brightness", "brightness to", "set it to"]):
        level = int(match.group(1))
        ok = _set_brightness(level)

        if ok:
            msg = f"Brightness set to {level} percent."
            brain.event("task_success")
        else:
            msg = ("I couldn't set the brightness. Many desktop monitors "
                   "require adjusting brightness using physical buttons.")
            brain.event("user_confused")

        return {
            "success": ok,
            "message": msg,
            "data": {"level": level, "action": "set"},
        }

    # Increase
    if any(w in q for w in ["up", "increase", "brighter", "raise"]):
        new = min(100, (current or 50) + 10)
        ok = _set_brightness(new)

        msg = (
            f"Brightness up to {new} percent."
            if ok else
            "Brightness control isn't available on this monitor."
        )

        brain.event("task_success" if ok else "user_confused")

        return {
            "success": ok,
            "message": msg,
            "data": {"level": new, "action": "increase"},
        }

    # Decrease
    if any(w in q for w in ["down", "decrease", "dimmer", "lower", "dim"]):
        new = max(0, (current or 50) - 10)
        ok = _set_brightness(new)

        msg = (
            f"Brightness down to {new} percent."
            if ok else
            "Brightness control isn't available on this monitor."
        )

        brain.event("task_success" if ok else "user_confused")

        return {
            "success": ok,
            "message": msg,
            "data": {"level": new, "action": "decrease"},
        }

    # Read brightness
    if current is not None:
        brain.event("task_success")
        return {
            "success": True,
            "message": f"Screen brightness is at {current} percent.",
            "data": {"level": current, "action": "read"},
        }

    brain.event("user_confused")
    return {
        "success": False,
        "message": "I can't read brightness on this monitor.",
        "data": {"action": "read_failed"},
    }
