"""
jokes.py — JARVIS Command
Tell a random joke using icanhazdadjoke.com with offline fallback.
"""

from Desktop_Assistant import imports as I
import urllib.request
import json
import random
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "jokes"
COMMAND_ALIASES: List[str] = ["joke", "tell me a joke", "say a joke", "funny"]
COMMAND_DESCRIPTION: str = "Tells a random joke from an online API or offline fallback."
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
# Offline fallback jokes
# ---------------------------------------------------------------------------

FALLBACK_JOKES = [
    "Why don't scientists trust atoms? Because they make up everything.",
    "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I asked the IT guy how to make a computer fast. He said, stop feeding it.",
    "Why did the scarecrow win an award? Because he was outstanding in his field.",
]


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
            "message": f"The jokes command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    # ----------------------------------------------------------------------
    # Try online joke API
    # ----------------------------------------------------------------------
    try:
        req = urllib.request.Request(
            "https://icanhazdadjoke.com/",
            headers={"Accept": "application/json", "User-Agent": "JARVIS/1.0"}
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            joke = json.loads(resp.read())["joke"]

        brain.event("task_success")
        brain.remember("jokes_told", joke)

        return {
            "success": True,
            "message": joke,
            "data": {"source": "online", "joke": joke},
        }

    except Exception:
        # ------------------------------------------------------------------
        # Offline fallback
        # ------------------------------------------------------------------
        joke = random.choice(FALLBACK_JOKES)

        brain.event("task_success")
        brain.remember("jokes_told", joke)

        return {
            "success": True,
            "message": joke,
            "data": {"source": "offline", "joke": joke},
        }
