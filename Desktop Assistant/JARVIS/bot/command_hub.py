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
from bot.context import ctx

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
    "skip":        "media_control",
    "next":        "media_control",
    "resume":      "media_control",
    # DJ
    "queue":       "dj",
    "shuffle":     "dj",
    "dj":          "dj",
    "hype":        "dj",
    # Playlists / taste
    "playlist":    "playlists",
    "playlists":   "playlists",
    "taste":       "playlists",
}


def _load_registry() -> dict:
    with open(REGISTRY_PATH, "r") as f:
        return json.load(f)


def _match_command(query: str, registry: dict) -> tuple[str | None, dict | None, float]:
    """
    Match query to the best command using intent context + longest trigger.
    Returns (command_key, command_entry, confidence_score).
    confidence_score:
      0.90 = INTENT_CONTEXT hit
      0.65 = longest trigger, high specificity (trigger len >= 10)
      0.50 = longest trigger, low specificity
      0.00 = no match
    Context boost from bot.context is added on top, capped at 1.0.
    """
    query_lower = query.lower().strip()
    commands = registry.get("commands", {})

    # ── Step 1: Intent context check ─────────────────────────────────────────
    for word in query_lower.split():
        if word in INTENT_CONTEXT:
            target_key = INTENT_CONTEXT[word]
            if target_key in commands and commands[target_key].get("enabled", True):
                base = 0.90
                boost = ctx.get_confidence_boost(target_key)
                return target_key, commands[target_key], min(1.0, base + boost)

    for phrase, target_key in INTENT_CONTEXT.items():
        if " " in phrase and phrase in query_lower:
            if target_key in commands and commands[target_key].get("enabled", True):
                base = 0.90
                boost = ctx.get_confidence_boost(target_key)
                return target_key, commands[target_key], min(1.0, base + boost)

    # ── Step 2: Longest trigger wins ─────────────────────────────────────────
    all_entries = []
    for key, entry in commands.items():
        for trigger in entry.get("triggers", []):
            all_entries.append((len(trigger), trigger, key, entry))
    all_entries.sort(reverse=True)

    for trigger_len, trigger, key, entry in all_entries:
        if trigger.lower() in query_lower:
            base  = 0.65 if trigger_len >= 10 else 0.50
            boost = ctx.get_confidence_boost(key)
            return key, entry, min(1.0, base + boost)

    return None, None, 0.0


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
    command_key, command_entry, confidence = _match_command(query, registry)

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

    # ── Disambiguation ────────────────────────────────────────────────────────
    threshold = ctx.disambiguation_threshold
    if confidence < threshold:
        label = command_key.replace("_", " ")
        speak(f"Did you mean {label}?")
        log_event(f"Disambiguating '{query}' → '{command_key}' (confidence {confidence:.2f})")
        try:
            from bot.listener import listen_once, is_cancel
            response = listen_once(timeout=ctx.disambiguation_timeout)
            if not response or is_cancel(response):
                speak("Never mind.")
                return "CANCELLED"
            positive = any(w in response.lower() for w in
                           ["yes", "yeah", "yep", "correct", "sure", "do it",
                            "that's right", "affirmative", "go ahead", "please"])
            if not positive:
                speak("Alright, cancelled.")
                return "CANCELLED"
        except Exception:
            pass  # If listener unavailable, proceed anyway

    # ── Execute ───────────────────────────────────────────────────────────────
    try:
        _bot_modules = {"toggle_voice"}
        if command_key in _bot_modules:
            module = importlib.import_module(f"bot.{command_key}")
        else:
            module = importlib.import_module(f"commands.{command_key}")
        result  = module.run(query)
        outcome = result if isinstance(result, str) else f"Command '{command_key}' executed"
        status  = _infer_status(outcome) if isinstance(result, str) else "SUCCESS"
        log_query(query=query, interpretation=command_key, outcome=outcome, status=status)

        # Record in context engine
        ctx.record_command(command_key, query)

        # Optional personality quip
        try:
            from bot.personality.engine import after_command, get_unprompted
            quip = after_command(status == "SUCCESS", command_key=command_key)
            if quip:
                speak(quip)
            else:
                # Small chance of unprompted one-liner
                line = get_unprompted()
                if line:
                    speak(line)
        except Exception:
            pass

        # Proactive suggestion (fires occasionally based on context)
        try:
            music_sug  = ctx.get_music_suggestion()
            other_sug  = ctx.get_suggestion()
            suggestion = music_sug or other_sug

            if suggestion:
                speak(suggestion)

                # For music suggestions, listen for yes/no response
                if music_sug:
                    try:
                        from bot.listener import listen_once, is_cancel
                        response = listen_once(timeout=6)
                        if response:
                            accepted = any(w in response.lower() for w in
                                           ["yes", "yeah", "sure", "do it",
                                            "go ahead", "please", "put it on",
                                            "yep", "absolutely"])
                            rejected = is_cancel(response) or any(
                                w in response.lower() for w in
                                ["no", "nope", "not now", "skip", "pass",
                                 "don't", "stop"])
                            if accepted:
                                # Extract the query from the suggestion text
                                import re as _re
                                m = _re.search(
                                    r"You usually listen to (.+?) around",
                                    music_sug)
                                if m:
                                    import importlib as _il
                                    _dj = _il.import_module("commands.dj")
                                    _dj.record_suggestion_response(
                                        m.group(1), ctx.get_time_mode(), True)
                                    _dj.run(f"play {m.group(1)}")
                            elif rejected:
                                import re as _re
                                m = _re.search(
                                    r"You usually listen to (.+?) around",
                                    music_sug)
                                if m:
                                    import importlib as _il
                                    _dj = _il.import_module("commands.dj")
                                    _dj.record_suggestion_response(
                                        m.group(1), ctx.get_time_mode(), False)
                    except Exception:
                        pass
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