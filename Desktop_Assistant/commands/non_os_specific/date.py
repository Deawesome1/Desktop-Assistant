"""
date.py — JARVIS Command
Tell today's date in a natural, human-friendly format.
"""

from Desktop_Assistant import imports as I
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "date"
COMMAND_ALIASES: List[str] = ["today", "what day", "date today"]
COMMAND_DESCRIPTION: str = "Tells today's date."
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
    brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    if args is None:
        args = []
    if context is None:
        context = {}

    os_key = I.os_key()
    if not is_supported_on_os(os_key):
        return {
            "success": False,
            "message": f"The date command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    today = datetime.now().strftime("%A, %B %d, %Y")
    response = f"Today is {today}."

    # Brain integration
    brain.event("task_success")
    brain.remember("date_queries", response)

    return {
        "success": True,
        "message": response,
        "data": {
            "date_string": today,
            "datetime_obj": datetime.now().isoformat(),
        },
    }
