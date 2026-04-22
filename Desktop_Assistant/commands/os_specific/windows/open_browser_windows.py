"""
open_browser_windows.py — JARVIS Command (Windows)
Open the browser or perform a Google search.
"""

from Desktop_Assistant import imports as I
import webbrowser
from urllib.parse import quote
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "open_browser"
COMMAND_ALIASES: List[str] = [
    "open browser", "search for", "google", "look up", "search"
]
COMMAND_DESCRIPTION: str = "Opens the browser or performs a Google search on Windows."
COMMAND_OS_SUPPORT: List[str] = ["windows"]
COMMAND_CATEGORY: str = "web"
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
    prefixes = ["search for", "google", "look up", "search"]

    # Extract search term
    for prefix in prefixes:
        if prefix in q:
            term = q.split(prefix, 1)[-1].strip()
            if term:
                url = f"https://www.google.com/search?q={quote(term)}"
                webbrowser.open(url)

                brain.event("task_success")
                brain.remember("browser_searches", term)

                return {
                    "success": True,
                    "message": f"Searching for {term}.",
                    "data": {"action": "search", "term": term, "url": url},
                }

    # No search term → open homepage
    webbrowser.open("https://www.google.com")

    brain.event("task_success")
    brain.remember("browser_actions", "opened_homepage")

    return {
        "success": True,
        "message": "Opening your browser.",
        "data": {"action": "open_homepage"},
    }
