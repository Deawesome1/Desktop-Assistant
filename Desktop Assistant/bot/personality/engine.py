"""
bot/personality/engine.py — JARVIS personality engine.

Handles:
  - Response selection with randomisation
  - Situational humor (late night, repeated commands, mishear, obvious)
  - Unprompted one-liners
  - Small talk matching
  - After-command quips
  - Context-aware humor (weather, music, system state)

Profile loaded from bot/personality/{name}/profile.json
"""

import os
import json
import random
import time
from datetime import datetime

_PERSONALITY_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH     = os.path.join(_PERSONALITY_DIR, "..", "..", "config", "personality.json")

# ── State ─────────────────────────────────────────────────────────────────────
_profile:          dict       = {}
_active_name:      str        = "jarvis"
_command_counts:   dict       = {}   # command_key → count this session
_last_quip_time:   float      = 0.0
_session_requests: int        = 0
_last_unprompted:  float      = 0.0
_QUIP_COOLDOWN     = 12.0     # seconds between quips
_UNPROMPTED_MIN    = 180.0    # seconds between unprompted lines


def _load_profile(name: str = "jarvis") -> dict:
    path = os.path.join(_PERSONALITY_DIR, name, "profile.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        print(f"[Personality] Failed to load '{name}': using defaults.")
        return {}


def _active() -> dict:
    global _profile, _active_name
    if not _profile:
        try:
            with open(_CONFIG_PATH) as f:
                cfg = json.load(f)
            _active_name = cfg.get("active", "jarvis")
        except Exception:
            _active_name = "jarvis"
        _profile = _load_profile(_active_name)
    return _profile


def reload(name: str | None = None):
    global _profile, _active_name
    if name:
        _active_name = name
    _profile = _load_profile(_active_name)


# ── Core helpers ──────────────────────────────────────────────────────────────

def _pick(pool: list | None, fallback: str = "") -> str | None:
    if not pool:
        return fallback or None
    return random.choice(pool)


def _should_quip(wit_boost: float = 0.0) -> bool:
    p    = _active()
    rate = p.get("traits", {}).get("wit_level", 0.7) + wit_boost
    return random.random() < rate and (time.time() - _last_quip_time) > _QUIP_COOLDOWN


def _mark_quip():
    global _last_quip_time
    _last_quip_time = time.time()


# ── Public API ────────────────────────────────────────────────────────────────

def get_response(key: str) -> str | None:
    """Return a randomised response string for a system event key."""
    p = _active()
    pool = p.get("responses", {}).get(key, [])
    return _pick(pool)


def greet() -> str | None:
    """Return a greeting based on time of day."""
    p    = _active()
    hour = datetime.now().hour
    if 5 <= hour < 12:
        pool = p.get("small_talk", {}).get("how_are_you", [])
    elif 18 <= hour < 23:
        pool = p.get("small_talk", {}).get("how_are_you", [])
    else:
        pool = p.get("small_talk", {}).get("how_are_you", [])
    greeting = p.get("responses", {}).get("greeting", [])
    return _pick(greeting)


def after_command(success: bool = True, command_key: str = "") -> str | None:
    """
    Return an optional quip after a command completes.
    Tracks repetition for repeated-command humor.
    """
    global _session_requests
    _session_requests += 1

    p = _active()

    # Track command repetition
    if command_key:
        _command_counts[command_key] = _command_counts.get(command_key, 0) + 1
        count = _command_counts[command_key]
        if count >= 3 and _should_quip(0.2):
            repeated = p.get("quips", {}).get("repeated_command", [])
            if repeated:
                line = _pick(repeated)
                if line:
                    _mark_quip()
                    return line.replace("{n}", str(count))

    if not _should_quip():
        return None

    _mark_quip()
    hour = datetime.now().hour
    # Late night wit boost
    if hour >= 22 or hour < 4:
        late = p.get("quips", {}).get("late_night", [])
        if late and random.random() < 0.4:
            return _pick(late)

    quips = p.get("quips", {})
    pool  = quips.get("after_success", []) if success else quips.get("after_failure", [])
    return _pick(pool)


def get_small_talk(query: str) -> str | None:
    """Match query to small talk category and return a response."""
    p = _active()
    st = p.get("small_talk", {})
    q  = query.lower().strip()

    # Map query patterns to profile keys
    MATCHERS = [
        (["how are you", "how're you", "how do you feel", "you good",
          "you okay", "you alright"],              "how_are_you"),
        (["what are you", "who are you", "what is jarvis",
          "what exactly are you"],                 "what_are_you"),
        (["are you real", "are you alive", "are you sentient",
          "do you think", "do you feel"],          "are_you_real"),
        (["you're amazing", "you're great", "you're awesome",
          "you're incredible", "you're the best",
          "well done", "nice work", "impressive"],  "compliment"),
        (["thanks", "thank you", "cheers", "appreciate it",
          "appreciate you"],                        "thanks"),
        (["good job", "great job", "nice job", "good work",
          "great work", "well done"],               "good_job"),
        (["shut up", "be quiet", "stop talking",
          "quiet", "silence"],                      "shut_up"),
        (["i'm bored", "im bored", "i am bored",
          "nothing to do", "entertain me"],         "bored"),
        (["what time", "whats the time"],           "what_time_is_it"),
        (["do you dream", "do you sleep", "you don't sleep",
          "you never sleep", "are you always on"],  "ai_humor"),
        (["iron man", "tony stark", "avengers", "marvel",
          "hal 9000", "movie", "film"],             "pop_culture"),
        (["we're all going to die", "nothing matters",
          "existential", "the void"],               "dark_humor"),
        (["you remember", "you know everything", "you're always right",
          "you're never wrong"],                    "roast"),
        (["interesting fact", "tell me something", "random thought",
          "surprise me"],                           "absurdist"),
    ]

    for phrases, key in MATCHERS:
        if any(ph in q for ph in phrases):
            pool = st.get(key, [])
            if pool:
                return _pick(pool)

    # Roast energy for very short/vague queries
    if len(q.split()) <= 2 and q not in ("hi", "hello", "hey"):
        roast = st.get("roast", [])
        if roast and random.random() < 0.25:
            return _pick(roast)

    return None


def get_situational(situation: str, **kwargs) -> str | None:
    """
    Return a humor line for a specific situation.

    Situations:
      mishear, obvious, late_night, repeated_command,
      weather_rain, weather_hot, late_night_music,
      morning_news, high_cpu, repeated_weather,
      dj_intro, dj_transition
    """
    p    = _active()
    hour = datetime.now().hour

    if not _should_quip(0.1):
        return None

    # Check context_humor first
    pool = p.get("context_humor", {}).get(situation, [])

    # Fall back to quips
    if not pool:
        pool = p.get("quips", {}).get(situation, [])

    if not pool:
        return None

    _mark_quip()
    line = _pick(pool)
    if line and kwargs:
        for k, v in kwargs.items():
            line = line.replace("{" + k + "}", str(v))
    return line


def get_unprompted() -> str | None:
    """
    Occasionally return an unprompted one-liner.
    Fires at most once every UNPROMPTED_MIN seconds.
    """
    global _last_unprompted
    p = _active()
    if (time.time() - _last_unprompted) < _UNPROMPTED_MIN:
        return None
    if random.random() > 0.15:   # 15% chance when cooldown elapsed
        return None
    pool = p.get("quips", {}).get("unprompted", [])
    if not pool:
        return None
    _last_unprompted = time.time()
    line = _pick(pool)
    if line:
        line = line.replace("{count}", str(_session_requests))
    return line


def get_dj_intro() -> str | None:
    p    = _active()
    pool = p.get("quips", {}).get("dj_intro", [])
    return _pick(pool)


def get_dj_transition() -> str | None:
    p    = _active()
    pool = p.get("quips", {}).get("dj_transition", [])
    return _pick(pool)


def should_quip() -> bool:
    return _should_quip()