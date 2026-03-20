"""
command_hub.py — JARVIS central command router.

Matching strategy (in order):
  1. Intent disambiguation — commands can declare exclusive context keywords
     that make them win even if a shorter trigger matched another command.
     e.g. "start stopwatch" → stopwatch wins over open_app's "start"
  2. Longest trigger wins — prevents short triggers swallowing longer ones.
  3. First match — fallback if no length advantage.
"""

import os
import json
import importlib
import platform_utils  # registers JARVIS.platform_utils alias — must be first

from logs.logger import log_query, log_error, log_event
from bot.speaker import speak, get_response

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "commands.json")

FAILURE_PREFIXES = (
    "failed", "error", "couldn't", "could not",
    "not installed", "no ",
)

# Intent context map — if any of these words appear in the query,
# the listed command wins regardless of trigger length.
# Format: { "context_word": "command_key_that_wins" }
INTENT_CONTEXT: dict[str, str] = {
    # Time / system
    "stopwatch":   "stopwatch",
    "lap":         "stopwatch",
    "uptime":      "system_info",
    "brightness":  "brightness",
    "volume":      "volume",
    "screenshot":  "screenshot",
    "reminder":    "reminder",
    "remind":      "reminder",
    "alarm":       "reminder",
    "timer":       "timer",
    "countdown":   "timer",
    "processes":   "top_processes",
    "recycle":     "recycle_bin",
    "trash":       "recycle_bin",
    "wifi":        "wifi_info",
    "clipboard":   "clipboard",
    "note":        "note",
    # Knowledge
    "wikipedia":   "wikipedia",
    "wiki":        "wikipedia",
    "define":      "dictionary",
    "definition":  "dictionary",
    "meaning":     "dictionary",
    # Web / media
    "weather":     "weather",
    "forecast":    "weather",
    "temperature": "weather",
    "news":        "news",
    "headlines":   "news",
    "youtube":     "youtube",
    "convert":     "converter",
    "conversion":  "converter",
    "joke":        "jokes",
    "calculate":   "calculator",
}


def _load_registry() -> dict:
    with open(REGISTRY_PATH, "r") as f:
        return json.load(f)


def _match_command(query: str, registry: dict) -> tuple[str | None, dict | None]:
    """
    Match query to the best command using intent context + longest trigger.
    """
    query_lower = query.lower().strip()
    commands = registry.get("commands", {})

    # ── Step 1: Intent context check ─────────────────────────────────────────
    # If a context keyword appears in the query, route directly to its owner.
    for word in query_lower.split():
        if word in INTENT_CONTEXT:
            target_key = INTENT_CONTEXT[word]
            if target_key in commands and commands[target_key].get("enabled", True):
                return target_key, commands[target_key]

    # Also check multi-word context phrases
    for phrase, target_key in INTENT_CONTEXT.items():
        if " " in phrase and phrase in query_lower:
            if target_key in commands and commands[target_key].get("enabled", True):
                return target_key, commands[target_key]

    # ── Step 2: Longest trigger wins ─────────────────────────────────────────
    all_entries = []
    for key, entry in commands.items():
        for trigger in entry.get("triggers", []):
            all_entries.append((len(trigger), trigger, key, entry))
    all_entries.sort(reverse=True)

    for _, trigger, key, entry in all_entries:
        if trigger.lower() in query_lower:
            return key, entry

    return None, None


def _infer_status(result: str) -> str:
    lowered = result.lower().strip()
    if any(lowered.startswith(p) for p in FAILURE_PREFIXES):
        return "FAILED"
    return "SUCCESS"


def handle(query: str) -> str:
    """
    Route a query to the right command module.
    Checks small talk first, then routes to commands.
    Returns the command result string, or a status sentinel on routing failure.
    """
    # ── Small talk check ──────────────────────────────────────────────────────
    try:
        import sys as _sys, os as _os
        # Ensure bot/ is importable regardless of working directory
        _bot_dir = _os.path.abspath(_os.path.join(_os.path.dirname(__file__)))
        _root    = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
        for _p in [_root, _bot_dir]:
            if _p not in _sys.path:
                _sys.path.insert(0, _p)
        from bot.personality.engine import get_small_talk
        reply = get_small_talk(query)
        if reply:
            speak(reply)
            log_event(f"Small talk: '{query}'")
            return "SUCCESS"
    except Exception as _st_err:
        pass

    registry = _load_registry()
    command_key, command_entry = _match_command(query, registry)

    if command_key is None:
        log_query(query=query, interpretation="No match found",
                  outcome="Command not found in registry", status="NOT_FOUND")
        speak(get_response("command_not_found"))
        return "NOT_FOUND"

    if command_entry is None or not command_entry.get("enabled", True):
        log_query(query=query, interpretation=command_key,
                  outcome=f"Command '{command_key}' is disabled", status="DISABLED")
        speak(get_response("command_disabled"))
        return "DISABLED"

    try:
        # Core bot modules override commands/ folder
        _bot_modules = {"toggle_voice"}
        if command_key in _bot_modules:
            module = importlib.import_module(f"bot.{command_key}")
        else:
            module = importlib.import_module(f"commands.{command_key}")
        result = module.run(query)
        outcome = result if isinstance(result, str) else f"Command '{command_key}' executed"
        status  = _infer_status(outcome) if isinstance(result, str) else "SUCCESS"
        log_query(query=query, interpretation=command_key, outcome=outcome, status=status)

        # Optional personality quip after command
        try:
            from bot.personality.engine import after_command
            quip = after_command(status == "SUCCESS")
            if quip:
                speak(quip)
        except Exception:
            pass

        return result if isinstance(result, str) else "SUCCESS"

    except ModuleNotFoundError:
        msg = f"commands/{command_key}.py not found (in registry but file missing)"
        log_error(msg)
        log_query(query=query, interpretation=command_key, outcome=msg, status="FAILED")
        speak(get_response("command_failed"))
        return "FAILED"

    except Exception as e:
        msg = f"Command '{command_key}' raised {type(e).__name__}: {e}"
        log_error(msg, exc=e)
        log_query(query=query, interpretation=command_key, outcome=msg, status="FAILED")
        speak(get_response("command_failed"))
        return "FAILED"