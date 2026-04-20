"""
pause.py — JARVIS Command
Interrupts JARVIS mid‑speech and keeps the assistant awake for the next command
without requiring the wake word again.

Returns the sentinel "__STAY_AWAKE__" which the main loop checks to avoid
returning to idle mode.
"""

import pyttsx3
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "pause"
COMMAND_ALIASES: List[str] = [
    "hold on", "wait", "pause jarvis", "stop talking", "quiet", "pause"
]
COMMAND_DESCRIPTION: str = "Interrupts JARVIS and keeps the session awake."
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
            "message": f"The pause command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    # ----------------------------------------------------------------------
    # Interrupt TTS immediately
    # ----------------------------------------------------------------------
    try:
        engine = pyttsx3.init()
        engine.stop()
    except Exception:
        pass

    # Brain integration
    brain.event("task_success")
    brain.remember("interruptions", "pause_requested")

    # ----------------------------------------------------------------------
    # Return sentinel to keep assistant awake
    # ----------------------------------------------------------------------
    return {
        "success": True,
        "message": "Ready.",
        "data": {
            "sentinel": "__STAY_AWAKE__",
            "action": "pause",
        },
    }
