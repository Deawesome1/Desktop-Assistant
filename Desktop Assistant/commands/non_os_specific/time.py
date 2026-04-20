"""
time.py — JARVIS Command
Tell the current time in a natural, human‑friendly format.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "time"
COMMAND_ALIASES: List[str] = ["what time", "current time", "time now", "tell me the time"]
COMMAND_DESCRIPTION: str = "Tells the current time."
COMMAND_OS_SUPPORT: List[str] = ["windows", "macintosh", "linux"]
COMMAND_CATEGORY: str = "information"
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
            "message": f"The time command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    # Format time
    time_str = datetime.now().strftime("%I:%M %p").lstrip("0")
    response = f"The time is {time_str}."

    # Brain integration
    brain.event("task_success")
    brain.remember("time_queries", time_str)

    return {
        "success": True,
        "message": response,
        "data": {
            "time_string": time_str,
            "datetime_obj": datetime.now().isoformat(),
        },
    }
