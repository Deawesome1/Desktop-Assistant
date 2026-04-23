"""
greet.py — JARVIS Command
Simple greeting handler for natural conversation.
"""

from typing import Any, Dict, List, Optional

COMMAND_NAME = "greet"
COMMAND_ALIASES = ["hello", "hi", "hey", "yo", "greetings"]
COMMAND_DESCRIPTION = "Responds to greetings."
COMMAND_OS_SUPPORT = ["windows", "macintosh", "linux"]
COMMAND_CATEGORY = "general"
COMMAND_REQUIRES_INTERNET = False
COMMAND_REQUIRES_ADMIN = False


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


def run(brain, user_text: str, args: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None):
    brain.event("task_success")
    return {
        "success": True,
        "message": "Hello. I'm JARVIS. What do you need?",
        "data": {"input": user_text},
    }
