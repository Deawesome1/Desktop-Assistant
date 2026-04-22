"""
clipboard.py — JARVIS Command
Cross‑platform clipboard read + clear.

Supports:
    - Reading clipboard contents
    - Clearing clipboard
"""

from Desktop_Assistant import imports as I
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "clipboard"
COMMAND_ALIASES: List[str] = ["clip", "clipboard read", "clipboard clear"]
COMMAND_DESCRIPTION: str = "Reads or clears the system clipboard."
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
            "message": f"The clipboard command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    q = user_text.lower()

    # ----------------------------------------------------------------------
    # CLEAR CLIPBOARD
    # ----------------------------------------------------------------------
    if "clear" in q or "empty" in q or "wipe" in q:
        try:
            I.clear_clipboard()
            brain.event("task_success")
            brain.remember("clipboard_actions", "clipboard cleared")

            return {
                "success": True,
                "message": "Clipboard cleared.",
                "data": {"action": "clear"},
            }

        except Exception as e:
            brain.event("user_confused")
            return {
                "success": False,
                "message": "I couldn't clear the clipboard.",
                "data": {"error": str(e)},
            }

    # ----------------------------------------------------------------------
    # READ CLIPBOARD
    # ----------------------------------------------------------------------
    try:
        content = I.get_clipboard()
    except Exception as e:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "Clipboard could not be accessed.",
            "data": {"error": str(e)},
        }

    if not content:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "Your clipboard is empty.",
            "data": {"content": None},
        }

    preview = content.strip()[:200].replace("\n", " ")

    brain.event("task_success")
    brain.remember("clipboard_reads", preview)

    return {
        "success": True,
        "message": f"Your clipboard contains: {preview}",
        "data": {
            "content": content,
            "preview": preview,
            "length": len(content),
        },
    }
