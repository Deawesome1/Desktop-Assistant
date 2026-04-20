"""
note_windows.py — JARVIS Command (Windows)
Save spoken notes to Desktop/jarvis_notes.txt.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from brain import Brain
from bot.listener import listen_once
from JARVIS.platform_utils import get_desktop


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "note"
COMMAND_ALIASES: List[str] = [
    "note", "take a note", "note this", "write this down",
    "remember this", "make a note", "take note"
]
COMMAND_DESCRIPTION: str = "Saves a note to Desktop/jarvis_notes.txt on Windows."
COMMAND_OS_SUPPORT: List[str] = ["windows"]
COMMAND_CATEGORY: str = "productivity"
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
    return os_key == "windows"


# ---------------------------------------------------------------------------
# Public run() entrypoint
# ---------------------------------------------------------------------------

def run(
    brain: Brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    q = user_text.lower()

    # Extract content
    content = q
    prefixes = [
        "take a note", "note this", "write this down", "remember this",
        "make a note", "take note", "note"
    ]

    for prefix in prefixes:
        if prefix in q:
            content = q.split(prefix, 1)[-1].strip(" :,.")
            break

    # If no content → ask user
    if not content:
        heard = listen_once(timeout=8)
        if not heard:
            brain.event("user_confused")
            return {
                "success": False,
                "message": "I didn't catch anything. Note cancelled.",
                "data": {"error": "no_content"},
            }
        content = heard.strip()

    # Save note
    notes_file = os.path.join(get_desktop(), "jarvis_notes.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"[{timestamp}] {content}\n"

    try:
        with open(notes_file, "a", encoding="utf-8") as f:
            f.write(entry)

        brain.event("task_success")
        brain.remember("notes_saved", content)

        return {
            "success": True,
            "message": f"Noted: {content}",
            "data": {"content": content, "file": notes_file},
        }

    except Exception as e:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "I couldn't save the note.",
            "data": {"error": str(e)},
        }
