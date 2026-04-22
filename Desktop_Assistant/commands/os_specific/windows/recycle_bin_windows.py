"""
recycle_bin_windows.py — JARVIS Command (Windows)
Empty the Windows Recycle Bin using SHEmptyRecycleBinW.
"""

from Desktop_Assistant import imports as I
import subprocess
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "recycle_bin"
COMMAND_ALIASES: List[str] = ["empty recycle bin", "clear recycle bin", "empty trash", "clear trash"]
COMMAND_DESCRIPTION: str = "Empties the Windows Recycle Bin."
COMMAND_OS_SUPPORT: List[str] = ["windows"]
COMMAND_CATEGORY: str = "system"
COMMAND_REQUIRES_INTERNET: bool = False
COMMAND_REQUIRES_ADMIN: bool = False   # SHEmptyRecycleBinW does NOT require admin


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
# Helper: empty recycle bin
# ---------------------------------------------------------------------------

def _empty_recycle_bin() -> bool:
    try:
        # SHEmptyRecycleBinW via PowerShell COM Shell.Application
        cmd = [
            "powershell",
            "-Command",
            r'(New-Object -ComObject Shell.Application).NameSpace(0xA).Items() | '
            r'% { Remove-Item $_.Path -Recurse -Force -ErrorAction SilentlyContinue }'
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=8)
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public run() entrypoint
# ---------------------------------------------------------------------------

def run(
    brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    ok = _empty_recycle_bin()

    if ok:
        brain.event("task_success")
        brain.remember("trash_actions", "emptied")

        return {
            "success": True,
            "message": "Trash emptied.",
            "data": {"action": "empty"},
        }

    brain.event("user_confused")
    return {
        "success": False,
        "message": "I couldn't empty the trash.",
        "data": {"action": "empty_failed"},
    }
