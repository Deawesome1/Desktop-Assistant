"""
top_processes_windows.py — JARVIS Command (Windows)
Report the top CPU or RAM using processes.
"""

import time
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "top_processes"
COMMAND_ALIASES: List[str] = [
    "top processes", "what's using cpu", "what's running",
    "memory hog", "cpu hog", "ram hog"
]
COMMAND_DESCRIPTION: str = "Reports the top CPU or RAM using processes on Windows."
COMMAND_OS_SUPPORT: List[str] = ["windows"]
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

    try:
        import psutil
    except ImportError:
        return {
            "success": False,
            "message": "This command requires psutil. Run pip install psutil.",
            "data": {"error": "missing_dependency"},
        }

    q = user_text.lower()
    by_ram = any(w in q for w in ["ram", "memory", "mem"])

    # First pass
    procs = []
    for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
        try:
            procs.append(p.info)
        except Exception:
            pass

    # Second pass for accurate CPU
    time.sleep(0.5)
    for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
        try:
            for existing in procs:
                if existing["name"] == p.info["name"]:
                    existing["cpu_percent"] = p.info["cpu_percent"]
        except Exception:
            pass

    key = "memory_percent" if by_ram else "cpu_percent"
    label = "RAM" if by_ram else "CPU"

    top = sorted(
        procs,
        key=lambda x: x.get(key, 0) or 0,
        reverse=True
    )[:5]

    lines = []
    for p in top:
        val = p.get(key, 0) or 0
        lines.append(f"{p['name']} at {val:.1f}%")

    msg = f"Top {label} users: " + ", ".join(lines) + "."

    brain.event("task_success")
    brain.remember("top_process_queries", label.lower())

    return {
        "success": True,
        "message": msg,
        "data": {
            "sorted_by": label.lower(),
            "processes": top,
        },
    }
