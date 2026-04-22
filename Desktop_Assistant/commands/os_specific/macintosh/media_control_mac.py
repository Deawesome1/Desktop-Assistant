"""
media_volume_mac.py — JARVIS Command (macOS)
Unified media + volume control:
    - Media: play/pause/next/previous
    - Volume: set %, up/down, mute/unmute, read level
"""

from Desktop_Assistant import imports as I
import subprocess
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME = "media_volume"
COMMAND_ALIASES = [
    "volume", "sound", "mute", "unmute", "set volume",
    "media", "pause", "play", "next song", "previous song",
    "skip", "louder", "quieter"
]
COMMAND_DESCRIPTION = "Controls system volume and media playback on macOS."
COMMAND_OS_SUPPORT = ["macintosh"]
COMMAND_CATEGORY = "system"
COMMAND_REQUIRES_INTERNET = False
COMMAND_REQUIRES_ADMIN = False


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
    return os_key == "macintosh"


# ---------------------------------------------------------------------------
# MEDIA KEY MAP
# ---------------------------------------------------------------------------

MEDIA_KEYS = {
    "pause": "playpause",
    "play": "playpause",
    "stop": "playpause",
    "next": "nexttrack",
    "skip": "nexttrack",
    "next song": "nexttrack",
    "previous": "prevtrack",
    "back": "prevtrack",
    "last song": "prevtrack",
}


# ---------------------------------------------------------------------------
# VOLUME HELPERS (macOS)
# ---------------------------------------------------------------------------

def _set_volume(level: int) -> bool:
    try:
        subprocess.run(
            ["osascript", "-e", f"set volume output volume {level}"],
            capture_output=True, timeout=4
        )
        return True
    except Exception:
        return False


def _get_volume() -> Optional[int]:
    try:
        r = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)"],
            capture_output=True, text=True, timeout=4
        )
        return int(r.stdout.strip())
    except Exception:
        return None


def _mute(state: bool) -> bool:
    try:
        cmd = "true" if state else "false"
        subprocess.run(
            ["osascript", "-e", f"set volume output muted {cmd}"],
            capture_output=True, timeout=4
        )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# MAIN RUN
# ---------------------------------------------------------------------------

def run(
    brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
):
    re = I.re
    q = user_text.lower()

    # ------------------------------------------------------------
    # MEDIA CONTROL
    # ------------------------------------------------------------
    try:
        import pyautogui
    except ImportError:
        pyautogui = None

    for trigger, key in MEDIA_KEYS.items():
        if trigger in q:
            if not pyautogui:
                return {
                    "success": False,
                    "message": "Media control requires pyautogui.",
                    "data": {"error": "missing_dependency"},
                }

            try:
                pyautogui.press(key)
                brain.event("task_success")
                brain.remember("media_actions", trigger)

                return {
                    "success": True,
                    "message": f"Media: {trigger}.",
                    "data": {"action": trigger, "key": key},
                }
            except Exception as e:
                brain.event("user_confused")
                return {
                    "success": False,
                    "message": "I couldn't control media playback.",
                    "data": {"error": str(e)},
                }

    # ------------------------------------------------------------
    # VOLUME CONTROL
    # ------------------------------------------------------------

    if "unmute" in q:
        _mute(False)
        brain.event("task_success")
        return {"success": True, "message": "Unmuted.", "data": {"action": "unmute"}}

    if "mute" in q:
        _mute(True)
        brain.event("task_success")
        return {"success": True, "message": "Muted.", "data": {"action": "mute"}}

    match = re.search(r"(\d+)", q)
    if match and any(p in q for p in ["set volume", "volume to", "set it to"]):
        level = max(0, min(100, int(match.group(1))))
        _set_volume(level)

        brain.event("task_success")
        brain.remember("volume_actions", f"set:{level}")

        return {
            "success": True,
            "message": f"Volume set to {level} percent.",
            "data": {"action": "set", "level": level},
        }

    current = _get_volume()

    if any(w in q for w in ["up", "increase", "louder", "raise"]):
        new = min(100, (current or 50) + 10)
        _set_volume(new)

        brain.event("task_success")
        return {
            "success": True,
            "message": f"Volume up to {new} percent.",
            "data": {"action": "increase", "level": new},
        }

    if any(w in q for w in ["down", "decrease", "quieter", "lower"]):
        new = max(0, (current or 50) - 10)
        _set_volume(new)

        brain.event("task_success")
        return {
            "success": True,
            "message": f"Volume down to {new} percent.",
            "data": {"action": "decrease", "level": new},
        }

    if current is not None:
        brain.event("task_success")
        return {
            "success": True,
            "message": f"Volume is at {current} percent.",
            "data": {"action": "read", "level": current},
        }

    brain.event("user_confused")
    return {
        "success": False,
        "message": "I didn't catch a media or volume command.",
        "data": {"error": "no_match"},
    }
