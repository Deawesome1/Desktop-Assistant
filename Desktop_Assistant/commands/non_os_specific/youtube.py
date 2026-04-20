"""
youtube.py — JARVIS Command
Search YouTube or open a specific video/search page in the browser.

Examples:
    "youtube cats"
    "search youtube for lo-fi beats"
    "look up guitar tutorials on youtube"
    "open youtube"
"""

import re
import webbrowser
import urllib.parse
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "youtube"
COMMAND_ALIASES: List[str] = [
    "youtube", "search youtube", "play on youtube", "open youtube",
    "youtube search", "look up on youtube"
]
COMMAND_DESCRIPTION: str = "Searches YouTube or opens the YouTube homepage."
COMMAND_OS_SUPPORT: List[str] = ["windows", "macintosh", "linux"]
COMMAND_CATEGORY: str = "entertainment"
COMMAND_REQUIRES_INTERNET: bool = True
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
# Prefixes (longest-first)
# ---------------------------------------------------------------------------

PREFIXES = [
    "search youtube for",
    "play on youtube",
    "youtube search for",
    "youtube search",
    "search on youtube for",
    "search on youtube",
    "open youtube for",
    "look up on youtube",
    "look up youtube",
    "on youtube search",
    "on youtube look up",
    "on youtube",
]


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
            "message": f"The youtube command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    q = user_text.lower().strip()

    # Normalize STT errors like "youtubes"
    q = re.sub(r"\byoutubes\b", "youtube", q)

    search_term = ""

    # ----------------------------------------------------------------------
    # Special case: "look up X on youtube"
    # ----------------------------------------------------------------------
    m = re.search(r"look up (.+?) on youtube", q)
    if m:
        search_term = m.group(1).strip()

    # ----------------------------------------------------------------------
    # Prefix-based extraction
    # ----------------------------------------------------------------------
    if not search_term:
        for prefix in PREFIXES:
            if prefix in q:
                search_term = q.split(prefix, 1)[-1].strip()
                break

    # ----------------------------------------------------------------------
    # Fallback: extract term after "youtube"
    # ----------------------------------------------------------------------
    if not search_term:
        m = re.search(r"\byoutube\b\s*(.*)", q)
        if m:
            search_term = m.group(1).strip()

    # ----------------------------------------------------------------------
    # If no search term → open YouTube homepage
    # ----------------------------------------------------------------------
    if not search_term:
        webbrowser.open("https://www.youtube.com")

        brain.event("task_success")
        brain.remember("youtube_actions", "opened_homepage")

        return {
            "success": True,
            "message": "Opening YouTube.",
            "data": {"action": "open_homepage"},
        }

    # ----------------------------------------------------------------------
    # Perform YouTube search
    # ----------------------------------------------------------------------
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_term)}"
    webbrowser.open(url)

    response = f"Searching YouTube for {search_term}."

    brain.event("task_success")
    brain.remember("youtube_searches", search_term)

    return {
        "success": True,
        "message": response,
        "data": {
            "action": "search",
            "query": search_term,
            "url": url,
        },
    }
