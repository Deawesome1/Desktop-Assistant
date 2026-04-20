"""
stopwatch.py — JARVIS Command
Start, stop, lap, reset, and check a persistent stopwatch.

State is stored in sys.modules so it survives across imports.
"""

import sys
import time
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "stopwatch"
COMMAND_ALIASES: List[str] = [
    "timer", "stopwatch", "start stopwatch", "stop stopwatch",
    "lap timer", "reset stopwatch", "check stopwatch"
]
COMMAND_DESCRIPTION: str = "Controls a persistent stopwatch with start, stop, lap, reset, and status."
COMMAND_OS_SUPPORT: List[str] = ["windows", "macintosh", "linux"]
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
    return os_key in COMMAND_OS_SUPPORT


# ---------------------------------------------------------------------------
# Persistent stopwatch state
# ---------------------------------------------------------------------------

if "_jarvis_stopwatch_state" not in sys.modules:
    sys.modules["_jarvis_stopwatch_state"] = type(sys)("_jarvis_stopwatch_state")
    sys.modules["_jarvis_stopwatch_state"].data = {
        "start_time": None,
        "running": False,
        "laps": [],
    }

_state = sys.modules["_jarvis_stopwatch_state"].data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _elapsed() -> float:
    return (time.time() - _state["start_time"]) if _state["start_time"] else 0.0


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h} hours, {m} minutes, {s} seconds"
    if m:
        return f"{m} minutes and {s} seconds"
    return f"{s} seconds"


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
            "message": f"The stopwatch command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    q = user_text.lower()

    # ----------------------------------------------------------------------
    # RESET
    # ----------------------------------------------------------------------
    if "reset" in q or "clear" in q:
        _state["start_time"] = None
        _state["running"] = False
        _state["laps"] = []

        brain.event("task_success")
        brain.remember("stopwatch_actions", "reset")

        return {
            "success": True,
            "message": "Stopwatch reset.",
            "data": {"action": "reset"},
        }

    # ----------------------------------------------------------------------
    # LAP
    # ----------------------------------------------------------------------
    if "lap" in q:
        if not _state["running"]:
            brain.event("user_confused")
            return {
                "success": False,
                "message": "The stopwatch isn't running.",
                "data": {"action": "lap_failed"},
            }

        elapsed = _elapsed()
        _state["laps"].append(elapsed)

        brain.event("task_success")
        brain.remember("stopwatch_laps", f"Lap {len(_state['laps'])}: {_fmt(elapsed)}")

        return {
            "success": True,
            "message": f"Lap {len(_state['laps'])}: {_fmt(elapsed)}.",
            "data": {
                "action": "lap",
                "lap_number": len(_state["laps"]),
                "lap_time": elapsed,
                "formatted": _fmt(elapsed),
            },
        }

    # ----------------------------------------------------------------------
    # START
    # ----------------------------------------------------------------------
    if "start" in q or "begin" in q:
        if _state["running"]:
            elapsed = _elapsed()
            return {
                "success": True,
                "message": f"Stopwatch already running at {_fmt(elapsed)}.",
                "data": {
                    "action": "already_running",
                    "elapsed": elapsed,
                    "formatted": _fmt(elapsed),
                },
            }

        _state["start_time"] = time.time()
        _state["running"] = True

        brain.event("task_success")
        brain.remember("stopwatch_actions", "start")

        return {
            "success": True,
            "message": "Stopwatch started.",
            "data": {"action": "start"},
        }

    # ----------------------------------------------------------------------
    # STOP
    # ----------------------------------------------------------------------
    if "stop" in q or "end" in q:
        if not _state["running"]:
            brain.event("user_confused")
            return {
                "success": False,
                "message": "The stopwatch isn't running.",
                "data": {"action": "stop_failed"},
            }

        elapsed = _elapsed()
        _state["running"] = False
        _state["start_time"] = None

        brain.event("task_success")
        brain.remember("stopwatch_actions", f"stop at {_fmt(elapsed)}")

        return {
            "success": True,
            "message": f"Stopwatch stopped at {_fmt(elapsed)}.",
            "data": {
                "action": "stop",
                "elapsed": elapsed,
                "formatted": _fmt(elapsed),
            },
        }

    # ----------------------------------------------------------------------
    # STATUS
    # ----------------------------------------------------------------------
    if _state["running"]:
        elapsed = _elapsed()
        return {
            "success": True,
            "message": f"Stopwatch is at {_fmt(elapsed)}.",
            "data": {
                "action": "status_running",
                "elapsed": elapsed,
                "formatted": _fmt(elapsed),
            },
        }

    return {
        "success": True,
        "message": "Stopwatch is not running.",
        "data": {"action": "status_idle"},
    }
