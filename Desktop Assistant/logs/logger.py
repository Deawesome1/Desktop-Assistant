"""
JARVIS Logging Module — Drop‑in Version
Counts every interaction, records system activity, logs simplified errors,
and never throws fatal exceptions.

Log files:
  logs/jarvis.log
  logs/jarvis_stats.json
"""

import os
import json
import threading
from datetime import datetime

# ────────────────────────────────────────────────────────────────
# Paths
# ────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "jarvis.log")
STATS_FILE = os.path.join(BASE_DIR, "jarvis_stats.json")

os.makedirs(BASE_DIR, exist_ok=True)

# ────────────────────────────────────────────────────────────────
# Internal counters
# ────────────────────────────────────────────────────────────────

_lock = threading.Lock()

_sequence = 0          # global log entry number
_session_seq = 0       # entry number within this session
_session_id = 0        # increments each startup

_session_stats = {
    "interactions": 0,
    "commands_run": 0,
    "commands_passed": 0,
    "commands_failed": 0,
    "errors": 0,
}

# ────────────────────────────────────────────────────────────────
# Stats load/save
# ────────────────────────────────────────────────────────────────

def _load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "total_entries": 0,
        "total_sessions": 0,
        "all_time": {
            "interactions": 0,
            "commands_run": 0,
            "commands_passed": 0,
            "commands_failed": 0,
            "errors": 0,
        }
    }


def _save_stats(stats):
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────
# Initialize session
# ────────────────────────────────────────────────────────────────

def _init():
    global _sequence, _session_id

    stats = _load_stats()

    _sequence = stats.get("total_entries", 0)
    _session_id = stats.get("total_sessions", 0) + 1

    stats["total_sessions"] = _session_id
    _save_stats(stats)


_init()

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────

def _next_seq():
    global _sequence, _session_seq
    with _lock:
        _sequence += 1
        _session_seq += 1
        return _sequence, _session_seq


def _write(entry: dict):
    """Write a JSON log entry safely."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _flush_stats():
    stats = _load_stats()
    stats["total_entries"] = _sequence

    for k, v in _session_stats.items():
        stats["all_time"][k] = stats["all_time"].get(k, 0) + v

    _save_stats(stats)


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────

def log_interaction(event: str, detail: str = ""):
    """Logs any interaction: user message, reply, internal action."""
    g, s = _next_seq()

    with _lock:
        _session_stats["interactions"] += 1

    entry = {
        "seq": g,
        "session": _session_id,
        "session_seq": s,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": "interaction",
        "event": event,
        "detail": detail,
    }

    _write(entry)
    _flush_stats()


def log_command(command: str, status: str = "SUCCESS", detail: str = ""):
    """Logs command execution with simplified status."""
    g, s = _next_seq()

    with _lock:
        _session_stats["commands_run"] += 1
        if status == "SUCCESS":
            _session_stats["commands_passed"] += 1
        else:
            _session_stats["commands_failed"] += 1

    entry = {
        "seq": g,
        "session": _session_id,
        "session_seq": s,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": "command",
        "command": command,
        "status": status,
        "detail": detail,
    }

    _write(entry)
    _flush_stats()


def log_error(message: str, exc: Exception = None):
    """Logs simplified errors without tracebacks."""
    g, s = _next_seq()

    with _lock:
        _session_stats["errors"] += 1

    entry = {
        "seq": g,
        "session": _session_id,
        "session_seq": s,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": "error",
        "message": message,
        "exception": type(exc).__name__ if exc else None,
    }

    _write(entry)
    _flush_stats()


def get_session_stats():
    return {
        "session_id": _session_id,
        "session_entries": _session_seq,
        "global_entries": _sequence,
        **_session_stats,
    }
