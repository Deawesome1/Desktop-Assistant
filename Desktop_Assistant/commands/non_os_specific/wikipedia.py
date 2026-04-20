"""
wikipedia.py — JARVIS Command
Fetch a quick Wikipedia summary using the wikipedia-api library.

Examples:
    "wikipedia Alan Turing"
    "wiki black holes"
    "who is Ada Lovelace"
    "what is quantum computing"
"""

import re
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "wikipedia"
COMMAND_ALIASES: List[str] = [
    "wiki", "wikipedia", "who is", "who was", "what is", "what are", "tell me about"
]
COMMAND_DESCRIPTION: str = "Fetches a short Wikipedia summary using wikipedia-api."
COMMAND_OS_SUPPORT: List[str] = ["windows", "macintosh", "linux"]
COMMAND_CATEGORY: str = "information"
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
# Helper: extract subject from query
# ---------------------------------------------------------------------------

def _extract_subject(q: str) -> str:
    subject = q.strip()
    prefixes = [
        "wikipedia", "wiki", "who is", "who was",
        "what is", "what are", "tell me about"
    ]

    for prefix in prefixes:
        if prefix in q.lower():
            subject = q.lower().split(prefix, 1)[-1].strip(" ?")
            break

    return subject


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
            "message": f"The wikipedia command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    q = user_text.strip()
    subject = _extract_subject(q)

    if not subject:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "What would you like me to look up?",
            "data": {},
        }

    # ----------------------------------------------------------------------
    # Wikipedia lookup
    # ----------------------------------------------------------------------
    try:
        import wikipediaapi

        wiki = wikipediaapi.Wikipedia(
            language="en",
            user_agent="JARVIS/1.0"
        )

        page = wiki.page(subject)

        if not page.exists():
            brain.event("user_confused")
            return {
                "success": False,
                "message": f"I couldn't find a Wikipedia page for {subject}.",
                "data": {"subject": subject},
            }

        # First ~500 chars, trimmed to last full sentence
        summary = page.summary[:500].strip()
        last_period = summary.rfind(".")
        if last_period > 100:
            summary = summary[:last_period + 1]

        brain.event("task_success")
        brain.remember("wikipedia_queries", subject)

        return {
            "success": True,
            "message": summary,
            "data": {
                "subject": subject,
                "summary": summary,
                "page_title": page.title,
                "page_url": page.fullurl,
            },
        }

    except ImportError:
        return {
            "success": False,
            "message": "Wikipedia lookup requires the 'wikipedia-api' package. Run: pip install wikipedia-api",
            "data": {"error": "missing_dependency"},
        }

    except Exception as e:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "I had trouble fetching that from Wikipedia.",
            "data": {"error": str(e)},
        }
