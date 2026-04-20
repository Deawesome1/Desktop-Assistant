"""
timer.py — JARVIS Command
Set a countdown timer using natural‑language durations.

Examples:
    "set a timer for 5 minutes"
    "timer for 30 seconds"
    "set a 1 hour 20 minute timer"
"""

import re
import threading
import time
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "timer"
COMMAND_ALIASES: List[str] = [
    "set a timer", "timer", "countdown", "start timer",
    "remind me in", "timer for"
]
COMMAND_DESCRIPTION: str = "Sets a countdown timer that runs in the background."
COMMAND_OS_SUPPORT: List[str] = ["windows", "macintosh", "linux"]
COMMAND_CATEGORY: str = "utility"
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
    return os_key in COMMAND_OS_SUPPORT


# ---------------------------------------------------------------------------
# Public run() entrypoint
# ---------------------------------------------------------------------------

def run(
    brain: Brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    if args is None:
        args = []
    if context is None:
        context = {}

    os_key = brain.get_current_os_key()
    if not is_supported_on_os(os_key):
        return {
            "success": False,
            "message": f"The timer command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    q = user_text.lower()

    # ----------------------------------------------------------------------
    # Parse duration
    # ----------------------------------------------------------------------
    seconds = 0
    patterns = [
        (r"(\d+)\s*hour",   3600),
        (r"(\d+)\s*minute", 60),
        (r"(\d+)\s*second", 1),
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, q)
        if match:
            seconds += int(match.group(1)) * multiplier

    if seconds <= 0:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "I didn't catch how long. Try saying: set a timer for 5 minutes.",
            "data": {"parsed_seconds": seconds},
        }

    # ----------------------------------------------------------------------
    # Build human‑friendly label
    # ----------------------------------------------------------------------
    parts = []
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)

    if h:
        parts.append(f"{h} hour{'s' if h > 1 else ''}")
    if m:
        parts.append(f"{m} minute{'s' if m > 1 else ''}")
    if s:
        parts.append(f"{s} second{'s' if s > 1 else ''}")

    label = " and ".join(parts)

    # ----------------------------------------------------------------------
    # Start background countdown
    # ----------------------------------------------------------------------
    def _countdown():
        time.sleep(seconds)
        # Speak only after the delay
        try:
            from bot.speaker import speak
            speak(f"Your {label} timer is done.")
        except Exception:
            pass

    threading.Thread(target=_countdown, daemon=True).start()

    # Brain integration
    brain.event("task_success")
    brain.remember("timers_set", label)

    return {
        "success": True,
        "message": f"Timer set for {label}.",
        "data": {
            "duration_seconds": seconds,
            "label": label,
            "action": "timer_started",
        },
    }
