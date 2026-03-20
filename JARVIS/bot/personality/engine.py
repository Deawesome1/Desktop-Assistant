"""
personality/engine.py — JARVIS personality engine.

Loads the active personality profile and exposes:
  get_response(key)     — pick a random response for a system event
  get_quip(key)         — pick a random quip (may return "" for silence)
  get_small_talk(text)  — check if input is small talk, return reply or None
  should_quip()         — True if wit_level roll says fire a quip now
  greet()               — time-appropriate greeting

Usage:
    from personality.engine import get_response, get_quip, get_small_talk, greet
"""

import os
import json
import random
from datetime import datetime

_PERSONALITY_DIR = os.path.dirname(__file__)
_CONFIG_PATH     = os.path.join(_PERSONALITY_DIR, "..", "..", "config", "personality.json")

_profile_cache: dict | None = None
_active_name:   str  | None = None


def _load_profile() -> dict:
    global _profile_cache, _active_name

    # Read active personality name
    try:
        with open(_CONFIG_PATH) as f:
            active = json.load(f).get("active", "jarvis")
    except Exception:
        active = "jarvis"

    # Reload if personality changed or not yet loaded
    if _profile_cache is None or _active_name != active:
        profile_path = os.path.join(_PERSONALITY_DIR, active, "profile.json")
        try:
            with open(profile_path) as f:
                _profile_cache = json.load(f)
            _active_name = active
        except Exception as e:
            print(f"[Personality] Failed to load '{active}': {e}. Using defaults.")
            _profile_cache = _default_profile()
            _active_name = active

    return _profile_cache


def _default_profile() -> dict:
    return {
        "traits": {"wit_level": 1, "formality": 2, "sarcasm": 0, "warmth": 2},
        "responses": {
            "wake_acknowledged":   ["Yes?"],
            "waiting_for_command": ["What can I do for you?"],
            "cancelled":           ["Understood."],
            "command_not_found":   ["I couldn't find that command."],
            "command_disabled":    ["That command is disabled."],
            "command_failed":      ["Something went wrong."],
            "goodbye":             ["Goodbye."],
        },
        "quips":      {},
        "small_talk": {},
    }


def _pick(options: list[str]) -> str:
    """Pick a random non-empty option, or return first if all empty."""
    non_empty = [o for o in options if o.strip()]
    if not non_empty:
        return ""
    return random.choice(non_empty)


# ── Public API ────────────────────────────────────────────────────────────────

def get_response(key: str) -> str:
    """
    Get a randomised system response (wake acknowledged, cancelled, etc.)
    Falls back to the key string itself if not found.
    """
    profile = _load_profile()
    options = profile.get("responses", {}).get(key, [key])
    return _pick(options) if options else key


def get_quip(key: str) -> str:
    """
    Get a random quip for a given situation.
    Returns "" (empty string) when the personality decides to stay quiet —
    callers should check before speaking.
    """
    profile = _load_profile()
    options = profile.get("quips", {}).get(key, [""])
    return _pick(options)


def should_quip() -> bool:
    """
    Roll against wit_level to decide if a quip fires.
    wit_level 0 = never, 5 = always, 3 = ~60% of the time.
    """
    profile   = _load_profile()
    wit_level = profile.get("traits", {}).get("wit_level", 2)
    threshold = wit_level / 5.0
    return random.random() < threshold


def greet() -> str:
    """Return a time-appropriate greeting."""
    hour = datetime.now().hour
    profile = _load_profile()
    quips   = profile.get("quips", {})

    if 5 <= hour < 12:
        options = quips.get("greet_morning", ["Good morning."])
    elif 12 <= hour < 17:
        options = quips.get("greet_afternoon", ["Good afternoon."])
    elif 17 <= hour < 22:
        options = quips.get("greet_evening", ["Good evening."])
    else:
        options = quips.get("greet_generic", ["Hello."])

    return _pick(options)


def get_small_talk(text: str) -> str | None:
    """
    Check if the input is small talk.
    Returns a reply string if matched, None otherwise.

    Small talk is checked BEFORE command routing so JARVIS can respond
    naturally to "how are you" without needing a command entry.
    """
    profile    = _load_profile()
    small_talk = profile.get("small_talk", {})
    text_lower = text.lower().strip(" ?.,!")

    for phrase, responses in small_talk.items():
        if phrase in text_lower:
            # Responses can reference quip keys like ["compliment_response"]
            resolved = []
            for r in responses:
                quip_options = profile.get("quips", {}).get(r, None)
                if quip_options:
                    resolved.extend(quip_options)
                else:
                    resolved.append(r)
            return _pick([r for r in resolved if r])

    return None


def get_thinking() -> str:
    """Short acknowledgement while processing."""
    return get_quip("thinking") or "On it."


def after_command(success: bool) -> str:
    """
    Optionally spoken after a command completes.
    Returns "" if the personality decides to stay quiet.
    """
    if not should_quip():
        return ""
    key = "after_success" if success else "after_failure"
    return get_quip(key)


def reload():
    """Force reload of the personality profile (e.g. after editing profile.json)."""
    global _profile_cache
    _profile_cache = None
    _load_profile()
    print(f"[Personality] Reloaded: {_active_name}")