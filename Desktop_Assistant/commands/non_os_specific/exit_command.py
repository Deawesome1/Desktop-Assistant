"""
exit_command.py — JARVIS Command
Gracefully exit JARVIS or acknowledge a cancel request.

Triggers:
    "goodbye", "exit", "quit jarvis", "bye"
    (Soft cancel phrases like "cancel" or "never mind" are normally handled
     by the listener, but this command includes fallback handling.)
"""

import os
import time
from typing import Any, Dict, List, Optional
from Desktop_Assistant import imports as I


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "exit"
COMMAND_ALIASES: List[str] = ["quit", "goodbye", "bye", "exit jarvis", "quit jarvis"]
COMMAND_DESCRIPTION: str = "Exits JARVIS or acknowledges a cancel request."
COMMAND_OS_SUPPORT: List[str] = ["windows", "macintosh", "linux"]
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
            "message": f"The exit command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    q = user_text.lower()

    # ----------------------------------------------------------------------
    # Soft cancel (fallback)
    # ----------------------------------------------------------------------
    if any(w in q for w in ["cancel", "never mind", "nevermind", "stop"]):
        brain.event("task_success")
        brain.remember("exit_actions", "soft_cancel")
        return {
            "success": True,
            "message": "Okay.",
            "data": {"action": "soft_cancel"},
        }

    # ----------------------------------------------------------------------
    # Hard exit
    # ----------------------------------------------------------------------
    brain.event("task_success")
    brain.remember("exit_actions", "hard_exit")

    # Give TTS time to finish before terminating
    time.sleep(1.5)

    # Exit immediately
    os._exit(0)

    # (Unreachable, but required for type consistency)
    return {
        "success": True,
        "message": "Exiting JARVIS.",
        "data": {"action": "exit"},
    }
