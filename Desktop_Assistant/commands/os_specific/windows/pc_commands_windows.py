"""
pc_commands_windows.py — JARVIS Command (Windows)
Shutdown, restart, sleep, or lock the computer.

DISABLED by default in commands.json for safety.
"""

from Desktop_Assistant import imports as I
import os
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "pc_commands"
COMMAND_ALIASES: List[str] = [
    "shutdown", "restart", "reboot", "sleep", "hibernate", "lock", "turn off"
]
COMMAND_DESCRIPTION: str = "Controls shutdown, restart, sleep, and lock actions on Windows."
COMMAND_OS_SUPPORT: List[str] = ["windows"]
COMMAND_CATEGORY: str = "system"
COMMAND_REQUIRES_INTERNET: bool = False
COMMAND_REQUIRES_ADMIN: bool = True   # power actions often require elevated permissions


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
# Public run() entrypoint
# ---------------------------------------------------------------------------

def run(
    brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    q = user_text.lower()

    # ------------------------------------------------------------------
    # Restart
    # ------------------------------------------------------------------
    if "restart" in q or "reboot" in q:
        os.system("shutdown /r /t 10")

        brain.event("task_success")
        brain.remember("power_actions", "restart")

        return {
            "success": True,
            "message": "Restarting in 10 seconds.",
            "data": {"action": "restart"},
        }

    # ------------------------------------------------------------------
    # Sleep / Hibernate
    # ------------------------------------------------------------------
    if "sleep" in q or "hibernate" in q:
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

        brain.event("task_success")
        brain.remember("power_actions", "sleep")

        return {
            "success": True,
            "message": "Going to sleep.",
            "data": {"action": "sleep"},
        }

    # ------------------------------------------------------------------
    # Lock
    # ------------------------------------------------------------------
    if "lock" in q:
        os.system("rundll32.exe user32.dll,LockWorkStation")

        brain.event("task_success")
        brain.remember("power_actions", "lock")

        return {
            "success": True,
            "message": "Locking your PC.",
            "data": {"action": "lock"},
        }

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    if "shutdown" in q or "shut down" in q or "turn off" in q:
        os.system("shutdown /s /t 10")

        brain.event("task_success")
        brain.remember("power_actions", "shutdown")

        return {
            "success": True,
            "message": "Shutting down in 10 seconds.",
            "data": {"action": "shutdown"},
        }

    # ------------------------------------------------------------------
    # No match
    # ------------------------------------------------------------------
    brain.event("user_confused")
    return {
        "success": False,
        "message": "I didn't catch what you wanted. Say shutdown, restart, sleep, or lock.",
        "data": {"error": "no_match"},
    }
