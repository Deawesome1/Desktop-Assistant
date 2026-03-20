"""
logs/logger.py — JARVIS logging module.

Writes timestamped, sequenced logs to logs/jarvis.log.
Tracks per-session and all-time stats in logs/jarvis_stats.json.

Log entry format:
  {"seq": 42, "session": 3, "session_seq": 7, "timestamp": "...", ...}

  seq         — global entry number across all sessions ever
  session     — which run of JARVIS this is (increments each startup)
  session_seq — entry number within this session
"""

import os
import json
import logging
import threading
from datetime import datetime

LOG_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FILE   = os.path.join(LOG_DIR, "jarvis.log")
STATS_FILE = os.path.join(LOG_DIR, "jarvis_stats.json")

os.makedirs(LOG_DIR, exist_ok=True)

# ── Counters ──────────────────────────────────────────────────────────────────
_lock        = threading.Lock()
_sequence    = 0
_session_seq = 0
_session_id  = 0
_session_stats = {
    "commands_run": 0, "commands_passed": 0,
    "commands_failed": 0, "not_found": 0,
}


def _load_stats() -> dict:
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "total_entries": 0,
        "total_sessions": 0,
        "all_time": {
            "commands_run": 0, "commands_passed": 0,
            "commands_failed": 0, "not_found": 0,
        }
    }


def _save_stats(stats: dict):
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)
    except Exception:
        pass


def _init():
    global _sequence, _session_id
    stats = _load_stats()
    _sequence   = stats.get("total_entries", 0)
    _session_id = stats.get("total_sessions", 0) + 1
    stats["total_sessions"] = _session_id
    _save_stats(stats)


_init()

# ── Logger ────────────────────────────────────────────────────────────────────
_logger = logging.getLogger("JARVIS")
_logger.setLevel(logging.DEBUG)

if not _logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    _logger.addHandler(fh)
    _logger.addHandler(ch)


def _next() -> tuple[int, int]:
    global _sequence, _session_seq
    with _lock:
        _sequence    += 1
        _session_seq += 1
        return _sequence, _session_seq


def _flush_stats():
    stats = _load_stats()
    stats["total_entries"] = _sequence
    for k, v in _session_stats.items():
        stats["all_time"][k] = stats["all_time"].get(k, 0) + v
    _save_stats(stats)


# ── Public API ────────────────────────────────────────────────────────────────

def log_query(query: str, interpretation: str, outcome: str, status: str = "SUCCESS"):
    gseq, sseq = _next()
    with _lock:
        _session_stats["commands_run"] += 1
        if status == "SUCCESS":   _session_stats["commands_passed"] += 1
        elif status == "FAILED":  _session_stats["commands_failed"] += 1
        elif status == "NOT_FOUND": _session_stats["not_found"]     += 1

    entry = {
        "seq": gseq, "session": _session_id, "session_seq": sseq,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "query": query, "interpretation": interpretation,
        "outcome": outcome, "status": status,
    }
    _logger.info(json.dumps(entry))
    _flush_stats()


def log_event(message: str, level: str = "info"):
    gseq, sseq = _next()
    getattr(_logger, level.lower(), _logger.info)(
        f"[#{gseq} S{_session_id}:{sseq}] {message}"
    )
    _flush_stats()


def log_error(message: str, exc: Exception = None):
    gseq, sseq = _next()
    msg = f"[#{gseq} S{_session_id}:{sseq}] {message}"
    if exc:
        msg += f" | {type(exc).__name__}: {exc}"
    _logger.error(msg)
    _flush_stats()


def get_session_stats() -> dict:
    return {
        "session_id": _session_id,
        "session_entries": _session_seq,
        "global_entries": _sequence,
        **_session_stats,
    }


def print_session_summary():
    s = get_session_stats()
    print(f"\n  Session #{s['session_id']} Summary")
    print(f"  {'─'*30}")
    print(f"  Commands run:    {s['commands_run']}")
    print(f"  Passed:          {s['commands_passed']}")
    print(f"  Failed:          {s['commands_failed']}")
    print(f"  Not found:       {s['not_found']}")
    print(f"  Entries (session / total): {s['session_entries']} / {s['global_entries']}")
    print()