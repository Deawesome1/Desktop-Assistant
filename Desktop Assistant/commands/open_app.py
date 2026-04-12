"""
commands/open_app.py — Cross-platform app launcher/closer.
Uses app_scanner cache on Windows (Start Menu scan).
Falls back to direct command launch on Mac/Linux.
"""
import os
import sys
from difflib import get_close_matches, SequenceMatcher
from bot.speaker import speak
from bot.listener import listen_once, is_cancel
from JARVIS.platform_utils import IS_WINDOWS, IS_MAC, IS_LINUX, launch_app

CLOSE_WORDS  = ["close", "kill", "quit", "terminate", "exit"]
LAUNCH_WORDS = ["open", "launch", "run"]

# Mac/Linux common app commands (spoken name → command/path)
UNIX_APP_MAP = {
    # Mac
    "safari":        "open -a Safari",
    "finder":        "open -a Finder",
    "terminal":      "open -a Terminal",
    "activity monitor": "open -a 'Activity Monitor'",
    "system preferences": "open -a 'System Preferences'",
    "system settings":    "open -a 'System Settings'",
    "calculator":    "open -a Calculator",
    "notes":         "open -a Notes",
    "music":         "open -a Music",
    "photos":        "open -a Photos",
    # Linux / cross-platform
    "firefox":       "firefox",
    "chrome":        "google-chrome",
    "chromium":      "chromium-browser",
    "files":         "nautilus",
    "gedit":         "gedit",
    "vlc":           "vlc",
    "spotify":       "spotify",
    "discord":       "discord",
    "vscode":        "code",
    "vs code":       "code",
    "steam":         "steam",
}


def _resolve_spoken(spoken: str) -> str:
    """Strip action words to get just the app name."""
    q = spoken.lower()
    for word in CLOSE_WORDS + LAUNCH_WORDS:
        q = q.replace(word + " ", "").replace(" " + word, "").strip()
    return q.strip()


def _fuzzy_find_unix(spoken: str) -> tuple[str, float] | tuple[None, float]:
    keys = list(UNIX_APP_MAP.keys())
    matches = get_close_matches(spoken, keys, n=1, cutoff=0.5)
    if not matches:
        return None, 0.0
    key = matches[0]
    score = SequenceMatcher(None, spoken, key).ratio()
    return key, score


def _close_process(name: str) -> str:
    try:
        import psutil
        killed = []
        for proc in psutil.process_iter(["name"]):
            try:
                if name.lower() in (proc.info["name"] or "").lower():
                    proc.kill()
                    killed.append(proc.info["name"])
            except Exception:
                pass
        if killed:
            return f"Closed {name}."
        return f"Failed: {name} doesn't appear to be running."
    except ImportError:
        return "Failed: closing apps requires psutil. Run pip install psutil."


def _confirm(question: str) -> bool:
    speak(question)
    response = listen_once(timeout=6)
    if not response:
        return False
    return any(w in response.lower() for w in ["yes", "yeah", "yep", "sure", "do it"])


def run(query: str) -> str:
    q      = query.lower().strip()
    spoken = _resolve_spoken(q)
    closing = any(w in q for w in CLOSE_WORDS)

    if not spoken:
        speak("Which app would you like me to open?")
        heard = listen_once(timeout=6)
        if not heard:
            return "Failed: no app name given."
        spoken = _resolve_spoken(heard)

    # ── Windows: use app_scanner cache ───────────────────────────────────────
    if IS_WINDOWS:
        try:
            from commands.app_scanner import get_cache, add_alias
            cache = get_cache()
            app, confidence, via_alias = _find_in_cache(spoken, cache)

            if app is None:
                speak(f"I couldn't find {spoken} in your app list.")
                return f"Failed: no match for '{spoken}'"

            if confidence < 0.75:
                action = "close" if closing else "open"
                confirmed = _confirm(f"Did you mean {app['name']}? Should I {action} it?")
                if not confirmed:
                    speak("Okay, cancelled.")
                    return "Cancelled."
                all_aliases = [a.lower() for a in app.get("aliases", [])]
                if spoken not in all_aliases and spoken != app["name_lower"]:
                    if _confirm(f"Should I remember {spoken} as {app['name']}?"):
                        add_alias(app["name_lower"], spoken)
                        speak(f"Got it. I'll remember {spoken} as {app['name']}.")

            if closing:
                result = _close_process(app["name"])
            else:
                config_path = os.path.join(os.path.dirname(__file__), "..", "config", "apps_config.json")
                import json
                allow_admin = False
                try:
                    with open(config_path) as f:
                        allow_admin = json.load(f).get("allow_admin", False)
                except Exception:
                    pass
                if app.get("requires_admin") and not allow_admin:
                    result = f"Failed: {app['name']} requires admin. Enable allow_admin in apps_config.json."
                else:
                    ok = launch_app(app.get("path", app["name"]))
                    result = f"Opening {app['name']}." if ok else f"Failed: couldn't open {app['name']}."

            speak(result)
            return result

        except Exception as e:
            speak(f"App scanner error: {e}")
            return f"Failed: {e}"

    # ── Mac / Linux: use UNIX_APP_MAP with fuzzy match ────────────────────────
    key, score = _fuzzy_find_unix(spoken)

    if key is None:
        speak(f"I don't know how to open {spoken} on this system. You can add it to UNIX_APP_MAP in open_app.py.")
        return f"Failed: no match for '{spoken}'"

    if score < 0.75:
        confirmed = _confirm(f"Did you mean {key}?")
        if not confirmed:
            speak("Okay, cancelled.")
            return "Cancelled."

    if closing:
        result = _close_process(key)
    else:
        cmd = UNIX_APP_MAP[key]
        ok  = launch_app(cmd)
        result = f"Opening {key}." if ok else f"Failed: couldn't launch {key}."

    speak(result)
    return result


def _find_in_cache(spoken: str, cache: dict) -> tuple[dict | None, float, bool]:
    spoken_lower = spoken.lower().strip()
    for app in cache.get("apps", []):
        if app["name_lower"] == spoken_lower:
            return app, 1.0, False
        for alias in app.get("aliases", []):
            if alias.lower() == spoken_lower:
                return app, 1.0, True
    for app in cache.get("apps", []):
        if spoken_lower in app["name_lower"]:
            return app, 0.9, False

    all_names = [a["name_lower"] for a in cache.get("apps", [])]
    matches = get_close_matches(spoken_lower, all_names, n=1, cutoff=0.5)
    if not matches:
        return None, 0.0, False

    matched = matches[0]
    score = SequenceMatcher(None, spoken_lower, matched).ratio()
    for app in cache.get("apps", []):
        if app["name_lower"] == matched:
            return app, score, False
    return None, 0.0, False