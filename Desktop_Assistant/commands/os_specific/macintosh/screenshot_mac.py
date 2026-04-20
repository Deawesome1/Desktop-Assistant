"""
screenshot_mac.py — JARVIS Command (macOS)
Take a screenshot and save it to the Desktop with a timestamped filename.
"""

import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional
from brain import Brain
from JARVIS.platform_utils import get_desktop


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "screenshot"
COMMAND_ALIASES: List[str] = ["screenshot", "take screenshot", "screen capture", "capture screen"]
COMMAND_DESCRIPTION: str = "Takes a screenshot and saves it to the Desktop on macOS."
COMMAND_OS_SUPPORT: List[str] = ["macintosh"]
COMMAND_CATEGORY: str = "utility"
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
    return os_key == "macintosh"


# ---------------------------------------------------------------------------
# Public run() entrypoint
# ---------------------------------------------------------------------------

def run(
    brain: Brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    desktop = get_desktop()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(desktop, f"screenshot_{timestamp}.png")

    try:
        # macOS native screenshot command
        subprocess.run(["screencapture", "-x", filename], timeout=8)

        brain.event("task_success")
        brain.remember("screenshots_taken", filename)

        return {
            "success": True,
            "message": f"Screenshot saved to Desktop as screenshot_{timestamp}.png.",
            "data": {"file": filename},
        }

    except Exception as e:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "I couldn't take a screenshot.",
            "data": {"error": str(e)},
        }
