"""
ip_address_mac.py — JARVIS Command (macOS)
Report the user's local or public IP address.

Examples:
    "what's my ip"
    "ip address"
    "public ip"
"""

import socket
import urllib.request
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "ip_address"
COMMAND_ALIASES: List[str] = [
    "ip address", "what's my ip", "my ip", "public ip", "external ip"
]
COMMAND_DESCRIPTION: str = "Reports the local or public IP address on macOS."
COMMAND_OS_SUPPORT: List[str] = ["macintosh"]
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
    return os_key == "macintosh"


# ---------------------------------------------------------------------------
# Public run() entrypoint
# ---------------------------------------------------------------------------

def run(
    brain: Brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    q = user_text.lower()

    # Local IP
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = None

    # Public IP
    if "public" in q or "external" in q:
        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=4) as resp:
                public_ip = resp.read().decode().strip()

            brain.event("task_success")
            brain.remember("ip_queries", f"public:{public_ip}")

            return {
                "success": True,
                "message": f"Your public IP address is {public_ip}.",
                "data": {"type": "public", "public_ip": public_ip},
            }

        except Exception as e:
            brain.event("user_confused")
            return {
                "success": False,
                "message": "I couldn't retrieve your public IP right now.",
                "data": {"type": "public", "error": str(e)},
            }

    # Local IP response
    if local_ip:
        brain.event("task_success")
        brain.remember("ip_queries", f"local:{local_ip}")

        return {
            "success": True,
            "message": f"Your local IP address is {local_ip}.",
            "data": {"type": "local", "local_ip": local_ip},
        }

    brain.event("user_confused")
    return {
        "success": False,
        "message": "I couldn't determine your local IP address.",
        "data": {"type": "local", "error": "lookup_failed"},
    }
