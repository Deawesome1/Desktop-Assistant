"""
clipboard_history.py — JARVIS Command
Track and recall clipboard history across the session.

Features:
    - Records clipboard changes (up to MAX_HISTORY)
    - Lists recent clipboard items
    - Recalls a specific item: "paste number 2", "clipboard item 3", etc.
"""

import tkinter as tk
import re
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "clipboard_history"
COMMAND_ALIASES: List[str] = ["clipboard", "cliphist", "clipboard history", "last copied"]
COMMAND_DESCRIPTION: str = "Tracks and recalls clipboard history."
COMMAND_OS_SUPPORT: List[str] = ["windows", "macintosh", "linux"]
COMMAND_CATEGORY: str = "system"
COMMAND_REQUIRES_INTERNET: bool = False
COMMAND_REQUIRES_ADMIN: bool = False

MAX_HISTORY = 10
_history: List[str] = []


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
# Internal clipboard helpers
# ---------------------------------------------------------------------------

def _get_clipboard() -> Optional[str]:
    """
    Safely read clipboard contents using tkinter.
    Returns None if clipboard is empty or inaccessible.
    """
    try:
        root = tk.Tk()
        root.withdraw()
        content = root.clipboard_get()
        root.destroy()
        content = content.strip()
        return content if content else None
    except Exception:
        return None


def _record_clipboard_change() -> None:
    """
    Capture clipboard changes and store them in history.
    """
    content = _get_clipboard()
    if content and (not _history or _history[-1] != content):
        _history.append(content)
        if len(_history) > MAX_HISTORY:
            _history.pop(0)


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
            "message": f"The clipboard history command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    # Always record clipboard before responding
    _record_clipboard_change()

    q = user_text.lower()

    # ----------------------------------------------------------------------
    # Recall specific item: "paste number 2", "clipboard 3", "item #4"
    # ----------------------------------------------------------------------
    m = re.search(r"(\d+)", q)
    if m and any(w in q for w in ["number", "item", "paste", "#"]):
        idx = int(m.group(1)) - 1

        if 0 <= idx < len(_history):
            item = _history[idx]
            preview = item[:100].replace("\n", " ")

            brain.event("task_success")
            brain.remember("clipboard_history", f"recalled item {idx+1}")

            return {
                "success": True,
                "message": f"Clipboard item {idx + 1}: {preview}",
                "data": {
                    "index": idx + 1,
                    "content": item,
                    "preview": preview,
                },
            }

        brain.event("user_confused")
        return {
            "success": False,
            "message": f"I only have {len(_history)} items in clipboard history.",
            "data": {"requested_index": idx + 1},
        }

    # ----------------------------------------------------------------------
    # List history
    # ----------------------------------------------------------------------
    if not _history:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "Clipboard history is empty.",
            "data": {"history": []},
        }

    # Show last 5 items
    recent_items = _history[-5:]
    previews = [
        item[:60].replace("\n", " ")
        for item in recent_items
    ]

    brain.event("task_success")
    brain.remember("clipboard_history", f"listed {len(_history)} items")

    return {
        "success": True,
        "message": f"I have {len(_history)} clipboard items.",
        "data": {
            "total_items": len(_history),
            "recent_previews": previews,
            "full_history": list(_history),
        },
    }
