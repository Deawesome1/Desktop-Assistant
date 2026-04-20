"""
commands/dj.py — JARVIS DJ system.

Handles music playback across YouTube Music, YouTube, Spotify, and local files.
Supports vibe-based requests, time-aware defaults, queue management,
now-playing detection, DJ mode personality, and pattern learning.

Triggers: see commands.json
"""

import os
import re
import sys
import json
import time
import webbrowser
import urllib.parse
from datetime import datetime

from bot.speaker import speak
from bot.context import ctx

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT      = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DJ_CONFIG = os.path.join(_ROOT, "config", "dj_config.json")
_CTX_PAT   = os.path.join(_ROOT, "config", "context_patterns.json")

# ── In-memory queue ───────────────────────────────────────────────────────────
_queue: list[dict] = []   # [{query, provider, added_at}]

# ── Config helpers ────────────────────────────────────────────────────────────

def _load_cfg() -> dict:
    try:
        with open(_DJ_CONFIG) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cfg(cfg: dict):
    try:
        with open(_DJ_CONFIG, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def _is_dj_mode() -> bool:
    return _load_cfg().get("dj_mode", False)


# ── Provider selection ────────────────────────────────────────────────────────

def _detect_provider() -> str:
    """
    Auto-detect best provider based on open apps, then fall back to config default.
    Priority: Spotify app > YouTube Music in browser > config default
    """
    cfg       = _load_cfg()
    open_apps = ctx.get_open_apps()

    if "spotify.exe" in open_apps and cfg.get("providers", {}).get("spotify", {}).get("enabled"):
        return "spotify"

    # Check if a browser is open — assume YouTube Music (configurable default)
    browser_procs = {"opera.exe", "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"}
    if open_apps & browser_procs:
        default = cfg.get("default_provider", "youtube_music")
        if cfg.get("providers", {}).get(default, {}).get("enabled"):
            return default

    return cfg.get("default_provider", "youtube_music")


def _get_provider_url(provider: str) -> str:
    cfg = _load_cfg()
    return cfg.get("providers", {}).get(provider, {}).get("url", "https://music.youtube.com/search?q=")


def _provider_label(provider: str) -> str:
    cfg = _load_cfg()
    return cfg.get("providers", {}).get(provider, {}).get("label", provider)


def _open_on_provider(query: str, provider: str):
    """Open a search query on the given provider."""
    if provider == "local":
        _play_local(query)
        return

    url = _get_provider_url(provider) + urllib.parse.quote(query)
    webbrowser.open(url)


def _play_local(query: str):
    """Search and play a local file matching the query."""
    cfg       = _load_cfg()
    music_dir = cfg.get("providers", {}).get("local", {}).get("music_dir", "")
    if not music_dir or not os.path.isdir(music_dir):
        speak("Local music directory isn't configured. "
              "Set music_dir in dj_config.json.")
        return
    query_lower = query.lower()
    for root, _, files in os.walk(music_dir):
        for f in files:
            if f.lower().endswith((".mp3", ".flac", ".wav", ".m4a")):
                if query_lower in f.lower():
                    path = os.path.join(root, f)
                    try:
                        os.startfile(path)
                        return
                    except Exception:
                        pass
    speak(f"Couldn't find '{query}' in your local music folder.")


# ── Vibe resolution ───────────────────────────────────────────────────────────

def _resolve_vibe(vibe_word: str) -> str:
    """Map a vibe word to a search query."""
    cfg   = _load_cfg()
    vibes = cfg.get("vibes", {})
    return vibes.get(vibe_word.lower(), f"{vibe_word} music playlist")


def _time_vibe() -> str:
    """Return the vibe appropriate for current time, accounting for learned patterns."""
    cfg       = _load_cfg()
    time_mode = ctx.get_time_mode()

    # Check learned patterns first — always reload fresh from disk
    patterns = _load_patterns()
    dj_pats  = patterns.get("dj_patterns", {})
    mode_pat = dj_pats.get(time_mode, {})
    plays    = mode_pat.get("plays", [])
    threshold = cfg.get("suggestion_threshold", 3)

    if plays and len(plays) >= threshold:
        from collections import Counter
        most_common = Counter(plays).most_common(1)[0][0]
        return most_common

    # Fall back to time defaults
    default_vibe = cfg.get("time_defaults", {}).get(time_mode, "chill")
    return _resolve_vibe(default_vibe)


# ── Pattern learning ──────────────────────────────────────────────────────────

def _load_patterns() -> dict:
    try:
        with open(_CTX_PAT) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_patterns(data: dict):
    try:
        with open(_CTX_PAT, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _extract_artist(query: str) -> str | None:
    """
    Try to extract an artist name from a search query.
    Simple heuristic: if query has no vibe/genre words, treat it as artist/song.
    """
    words = set(query.lower().split()) - _FILLER_WORDS
    if words and not words.issubset(_VIBE_WORDS):
        # Likely an artist name or song title — return as-is for genre lookup
        return query.strip()
    return None


def _record_play(query: str, time_mode: str):
    """
    Record a play to the pattern engine.

    Pattern structure per time_mode:
    {
      "plays":       [...],   # rolling last 50 queries
      "count":       int,     # total plays ever
      "suggestions": {        # per-query suggestion tracking
        "lofi hip hop": {
          "offered": int,     # times proactively suggested
          "accepted": int,    # times user said yes
          "rejected": int,    # times user said no
          "silenced": bool,   # True = stop suggesting this
        }
      }
    }
    """
    patterns = _load_patterns()
    dj_pats  = patterns.setdefault("dj_patterns", {})
    mode_pat = dj_pats.setdefault(time_mode, {
        "plays": [], "count": 0, "suggestions": {}
    })
    mode_pat["plays"].append(query)
    mode_pat["count"] = mode_pat.get("count", 0) + 1
    mode_pat["plays"] = mode_pat["plays"][-50:]
    # Ensure suggestions dict exists
    mode_pat.setdefault("suggestions", {})
    _save_patterns(patterns)


def record_suggestion_response(query: str, time_mode: str, accepted: bool):
    """
    Record whether the user accepted or rejected a proactive suggestion.
    After MAX_REJECTIONS consecutive rejections, silence that suggestion.
    Silencing is reversible — if the user manually plays the same thing
    3+ more times, suggestions reactivate.
    """
    MAX_REJECTIONS = 3
    patterns = _load_patterns()
    dj_pats  = patterns.setdefault("dj_patterns", {})
    mode_pat = dj_pats.setdefault(time_mode, {
        "plays": [], "count": 0, "suggestions": {}
    })
    sug = mode_pat.setdefault("suggestions", {}).setdefault(query, {
        "offered": 0, "accepted": 0, "rejected": 0, "silenced": False,
    })
    sug["offered"] = sug.get("offered", 0) + 1
    if accepted:
        sug["accepted"] = sug.get("accepted", 0) + 1
        sug["silenced"] = False   # re-activate if they eventually say yes
    else:
        sug["rejected"] = sug.get("rejected", 0) + 1
        if sug["rejected"] >= MAX_REJECTIONS:
            sug["silenced"] = True

    _save_patterns(patterns)


def _is_suggestion_silenced(query: str, time_mode: str) -> bool:
    """Check if a proactive suggestion has been silenced by repeated rejection."""
    patterns = _load_patterns()
    sug = (patterns.get("dj_patterns", {})
                   .get(time_mode, {})
                   .get("suggestions", {})
                   .get(query, {}))
    return sug.get("silenced", False)


def _check_reactivate(query: str, time_mode: str):
    """
    If a silenced suggestion has been manually played 3+ more times since
    silencing, reactivate it automatically.
    """
    patterns = _load_patterns()
    mode_pat = patterns.get("dj_patterns", {}).get(time_mode, {})
    sug      = mode_pat.get("suggestions", {}).get(query, {})
    if not sug.get("silenced"):
        return
    # Count recent manual plays (last 10 entries)
    recent = mode_pat.get("plays", [])[-10:]
    recent_count = recent.count(query)
    if recent_count >= 3:
        sug["silenced"] = False
        sug["rejected"] = 0  # reset rejection counter
        _save_patterns(patterns)


# ── Now playing ───────────────────────────────────────────────────────────────

def _get_now_playing() -> str | None:
    """
    Read the currently playing track from browser window title or Spotify.
    Works on Windows via win32gui.
    """
    try:
        import win32gui

        titles = []

        def _enum(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t:
                    titles.append(t)

        win32gui.EnumWindows(_enum, None)

        # Spotify app: title is usually "Artist - Song"
        for t in titles:
            if " - Spotify" in t:
                return t.replace(" - Spotify", "").strip()

        # YouTube Music browser tab
        for t in titles:
            if "YouTube Music" in t and " - " in t:
                return t.split(" - ")[0].strip()

        # YouTube browser tab
        for t in titles:
            if "YouTube" in t and " - " in t:
                part = t.split(" - ")[0].strip()
                if part and part != "YouTube":
                    return part

    except ImportError:
        pass
    except Exception:
        pass
    return None


# ── DJ mode announcements ─────────────────────────────────────────────────────

_DJ_INTROS = [
    "Alright, pulling this up now.",
    "Your wish, my command. Queuing it up.",
    "Good choice. Let me get that going.",
    "Coming right up.",
    "Consider it done.",
    "On it.",
    "Excellent taste. Playing now.",
    "DJ JARVIS on the ones and twos.",
    "I've heard worse requests.",
]

_DJ_TRANSITIONS = [
    "Next up —",
    "Following that with —",
    "And now —",
    "Transitioning to —",
]

import random

def _dj_intro(query: str) -> str:
    intro = random.choice(_DJ_INTROS)
    return f"{intro} {query}."


def _announce(query: str, provider: str):
    """Speak a DJ-mode announcement."""
    label = _provider_label(provider)
    if _is_dj_mode() and _load_cfg().get("dj_mode_announce", True):
        # Try personality engine first, fall back to local pool
        try:
            from bot.personality.engine import get_dj_intro
            line = get_dj_intro()
            speak(f"{line} {query}." if line else _dj_intro(query))
        except Exception:
            speak(_dj_intro(query))
    else:
        speak(f"Playing {query} on {label}.")


# ── Query parsing ─────────────────────────────────────────────────────────────

# Words that indicate a vibe request rather than a specific track
_VIBE_WORDS = {
    "chill", "lofi", "lo-fi", "hype", "focus", "sad", "happy", "party",
    "morning", "night", "late night", "aggressive", "rap", "classical",
    "jazz", "ambient", "workout", "sleep", "vibe", "vibes", "something",
    "anything", "music", "beats", "tunes",
}

# Filler words to strip before vibe detection
# so "hype me up" → "hype", "some music" → "music"
_FILLER_WORDS = {
    "me", "up", "a", "an", "the", "some", "my", "on", "in", "to",
    "for", "please", "now", "just", "really", "very",
}

_PROVIDER_WORDS = {
    "youtube music": "youtube_music",
    "youtube":       "youtube",
    "spotify":       "spotify",
    "local":         "local",
    "my files":      "local",
}


def _parse_query(raw: str) -> tuple[str, str, bool]:
    """
    Parse a DJ command into (search_query, provider, is_vibe).
    Returns the resolved search string, provider key, and whether it's vibe-based.
    """
    q = raw.lower().strip()

    # Strip command prefixes
    for prefix in sorted([
        "play something", "play some", "put on some", "put on",
        "play me some", "play me", "queue up", "queue", "play",
        "shuffle", "put on a", "play a",
    ], key=len, reverse=True):
        if q.startswith(prefix):
            q = q[len(prefix):].strip()
            break

    # Detect provider override ("on spotify", "on youtube", "via youtube music")
    provider = None
    for phrase, key in sorted(_PROVIDER_WORDS.items(), key=lambda x: len(x[0]), reverse=True):
        for connector in [f" on {phrase}", f" via {phrase}", f" from {phrase}", f" in {phrase}"]:
            if connector in q:
                q = q.replace(connector, "").strip()
                provider = key
                break
        if provider:
            break

    if not provider:
        provider = _detect_provider()

    # Strip filler words before vibe detection
    # "hype me up" → {"hype"}, "some music" → {"music"}
    meaningful = set(q.split()) - _FILLER_WORDS

    # is_vibe if all meaningful words are vibe words (or nothing left)
    is_vibe = not meaningful or meaningful.issubset(_VIBE_WORDS)

    if is_vibe:
        if not meaningful or meaningful == {"music"} or meaningful == {"beats"}                 or meaningful == {"tunes"} or meaningful == {"something"}                 or meaningful == {"anything"}:
            # Too generic — use time-aware default
            search = _time_vibe()
        else:
            # Specific vibe word like "hype", "chill", "lofi"
            vibe_word = next(iter(meaningful - {"music", "beats", "tunes",
                                                 "something", "anything",
                                                 "vibes", "vibe"}), None)
            search = _resolve_vibe(vibe_word) if vibe_word else _time_vibe()
    else:
        search = q

    return search, provider, is_vibe


# ── Queue management ──────────────────────────────────────────────────────────

def _queue_add(query: str, provider: str):
    _queue.append({"query": query, "provider": provider,
                   "added_at": datetime.now().strftime("%H:%M")})
    speak(f"Added '{query}' to the queue. {len(_queue)} item{'s' if len(_queue) != 1 else ''} queued.")


def _queue_next() -> bool:
    if not _queue:
        speak("The queue is empty.")
        return False
    item = _queue.pop(0)
    speak(f"Playing next: {item['query']}.")
    _open_on_provider(item["query"], item["provider"])
    return True


def _queue_read():
    if not _queue:
        speak("Nothing in the queue.")
        return
    speak(f"You have {len(_queue)} item{'s' if len(_queue) != 1 else ''} queued.")
    for i, item in enumerate(_queue, 1):
        speak(f"{i}: {item['query']} on {_provider_label(item['provider'])}.")


def _queue_clear():
    _queue.clear()
    speak("Queue cleared.")


# ── Main handler ──────────────────────────────────────────────────────────────

def run(query: str) -> str:
    q = query.lower().strip()
    cfg = _load_cfg()

    # ── DJ mode toggle ────────────────────────────────────────────────────────
    if any(x in q for x in ["dj mode on", "be my dj", "dj mode activate",
                              "activate dj mode"]):
        cfg["dj_mode"] = True
        _save_cfg(cfg)
        speak("DJ mode activated. I'll take it from here.")
        return "DJ mode on."

    if any(x in q for x in ["dj mode off", "dj mode deactivate",
                              "deactivate dj mode", "stop dj mode"]):
        cfg["dj_mode"] = False
        _save_cfg(cfg)
        speak("DJ mode off. Back to silent running.")
        return "DJ mode off."

    # ── Provider switch ───────────────────────────────────────────────────────
    for phrase, key in _PROVIDER_WORDS.items():
        if f"switch to {phrase}" in q or f"use {phrase}" in q:
            cfg["default_provider"] = key
            _save_cfg(cfg)
            speak(f"Switched default music provider to {_provider_label(key)}.")
            return f"Provider set to {key}."

    # ── Now playing ───────────────────────────────────────────────────────────
    if any(x in q for x in ["what's playing", "what is playing",
                              "what's this song", "what song is this",
                              "now playing", "current song"]):
        track = _get_now_playing()
        if track:
            speak(f"Currently playing: {track}.")
            return f"Now playing: {track}"
        speak("I can't read what's playing right now.")
        return "Could not detect now playing."

    # ── Queue operations ──────────────────────────────────────────────────────
    if any(x in q for x in ["what's in the queue", "show queue",
                              "read the queue", "what's queued"]):
        _queue_read()
        return f"Queue has {len(_queue)} items."

    if any(x in q for x in ["clear the queue", "clear queue", "empty queue"]):
        _queue_clear()
        return "Queue cleared."

    if any(x in q for x in ["play queue", "next in queue", "play next"]):
        _queue_next()
        return "Playing from queue."

    # ── Skip ──────────────────────────────────────────────────────────────────
    if any(x in q for x in ["skip", "next track", "next song"]):
        try:
            import pyautogui
            pyautogui.hotkey("nexttrack")
            speak("Skipping." if not _is_dj_mode() else "Moving on. Next track.")
        except ImportError:
            speak("pyautogui isn't installed — can't send media keys.")
        return "Skipped."

    # ── Queue add (without playing) ───────────────────────────────────────────
    is_queue = q.startswith("queue") and "play queue" not in q
    if is_queue:
        raw = re.sub(r'^queue\s*(up\s*)?', '', q).strip()
        search, provider, is_vibe = _parse_query(raw)
        _queue_add(search, provider)
        return f"Queued: {search}"

    # ── Play ──────────────────────────────────────────────────────────────────
    search, provider, is_vibe = _parse_query(q)
    time_mode = ctx.get_time_mode()

    # Record play for pattern learning (DJ patterns + taste profile)
    _record_play(search, time_mode)
    try:
        from commands.playlists import record_play as _rp
        artist = _extract_artist(search)
        _rp(search, artist, time_mode)
    except Exception:
        pass

    # Announce
    _announce(search, provider)

    # Open
    _open_on_provider(search, provider)

    # Context note: record in command history
    ctx.record_command("dj", query)

    if is_vibe:
        return f"Playing vibe '{search}' on {_provider_label(provider)}."
    return f"Playing '{search}' on {_provider_label(provider)}."