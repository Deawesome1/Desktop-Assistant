"""
pc_commands_mac.py — JARVIS Command (macOS)
Shutdown, restart, sleep, or lock the computer.

DISABLED by default in commands.json for safety.
"""

from Desktop_Assistant import imports as I
import subprocess
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "pc_commands"
COMMAND_ALIASES: List[str] = [
    "shutdown", "restart", "reboot", "sleep", "hibernate", "lock", "turn off"
]
COMMAND_DESCRIPTION: str = "Controls shutdown, restart, sleep, and lock actions on macOS."
COMMAND_OS_SUPPORT: List[str] = ["macintosh"]
COMMAND_CATEGORY: str = "system"
COMMAND_REQUIRES_INTERNET: bool = False
COMMAND_REQUIRES_ADMIN: bool = True   # macOS power actions require sudo


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
        subprocess.Popen(["sudo", "shutdown", "-r", "now"])

        brain.event("task_success")
        brain.remember("power_actions", "restart")

        return {
            "success": True,
            "message": "Restarting now.",
            "data": {"action": "restart"},
        }

    # ------------------------------------------------------------------
    # Sleep
    # ------------------------------------------------------------------
    if "sleep" in q or "hibernate" in q:
        subprocess.Popen(["pmset", "sleepnow"])

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
        subprocess.Popen([
            "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession",
            "-suspend"
        ])

        brain.event("task_success")
        brain.remember("power_actions", "lock")

        return {
            "success": True,
            "message": "Locking your Mac.",
            "data": {"action": "lock"},
        }

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    if "shutdown" in q or "shut down" in q or "turn off" in q:
        subprocess.Popen(["sudo", "shutdown", "-h", "now"])

        brain.event("task_success")
        brain.remember("power_actions", "shutdown")

        return {
            "success": True,
            "message": "Shutting down now.",
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
