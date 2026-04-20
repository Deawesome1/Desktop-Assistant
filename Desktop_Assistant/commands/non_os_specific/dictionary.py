"""
dictionary.py — JARVIS Command
Define a word using the Free Dictionary API (no API key required).

Examples:
    "define ephemeral"
    "what does ubiquitous mean"
    "meaning of entropy"
"""

import re
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "dictionary"
COMMAND_ALIASES: List[str] = ["define", "definition", "meaning", "what does"]
COMMAND_DESCRIPTION: str = "Provides definitions for English words using the Free Dictionary API."
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
            "message": f"The dictionary command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    # ----------------------------------------------------------------------
    # Extract the word from the query
    # ----------------------------------------------------------------------
    q = user_text.lower().strip(" ?.,")

    prefixes = [
        "what is the meaning of",
        "what's the meaning of",
        "definition of",
        "meaning of",
        "what does",
        "define",
    ]

    for prefix in sorted(prefixes, key=len, reverse=True):
        if q.startswith(prefix):
            q = q[len(prefix):].strip(" ?.,")
            break

    # Remove trailing "mean" or "means"
    q = re.sub(r"\s+means?$", "", q).strip(" ?.,")
    word = q.strip()

    if not word:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "Which word would you like me to define?",
            "data": {},
        }

    # ----------------------------------------------------------------------
    # Query the Free Dictionary API
    # ----------------------------------------------------------------------
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})

        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())

        entry = data[0]
        meanings = entry.get("meanings", [])

        if not meanings:
            brain.event("user_confused")
            return {
                "success": False,
                "message": f"I found '{word}' but couldn't get a definition.",
                "data": {"word": word},
            }

        part_of_speech = meanings[0].get("partOfSpeech", "")
        definition = meanings[0]["definitions"][0].get("definition", "")
        example = meanings[0]["definitions"][0].get("example", "")

        response = f"{word}: {part_of_speech}. {definition}"
        if example:
            response += f" For example: {example}"

        # Brain integration
        brain.event("task_success")
        brain.remember("dictionary_queries", f"{word}: {definition}")

        return {
            "success": True,
            "message": response,
            "data": {
                "word": word,
                "part_of_speech": part_of_speech,
                "definition": definition,
                "example": example,
            },
        }

    except urllib.error.HTTPError:
        brain.event("user_confused")
        return {
            "success": False,
            "message": f"I couldn't find a definition for '{word}'.",
            "data": {"word": word},
        }

    except Exception as e:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "I couldn't reach the dictionary right now.",
            "data": {"error": str(e)},
        }
