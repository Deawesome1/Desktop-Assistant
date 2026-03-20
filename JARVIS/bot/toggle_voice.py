"""
bot/toggle_voice.py — Mute or unmute JARVIS speech mid-session.
Lives in bot/ as core infrastructure.
Triggers: "mute jarvis", "unmute jarvis", "toggle voice", "silence", "be quiet"
Writes the change to config/voice.json so it persists across restarts.
"""
import os
import json
from bot.speaker import speak

# bot/ -> JARVIS/ -> config/voice.json
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "voice.json")


def _load() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _save(data: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def mute():
    data = _load()
    data["mute"] = True
    _save(data)
    print("[JARVIS]: Voice muted. Say 'unmute jarvis' to re-enable.")


def unmute():
    data = _load()
    data["mute"] = False
    _save(data)
    speak("Voice enabled.")


def toggle() -> bool:
    """Flip mute state. Returns True if now muted."""
    data = _load()
    data["mute"] = not data.get("mute", False)
    _save(data)
    return data["mute"]


def is_muted() -> bool:
    return _load().get("mute", False)


def run(query: str) -> str:
    """Command entry point — called by command_hub."""
    q = query.lower()
    data = _load()
    currently_muted = data.get("mute", False)

    if any(w in q for w in ["unmute", "unsilence", "speak again", "voice on", "turn on voice"]):
        data["mute"] = False
        _save(data)
        speak("Voice enabled.")
        return "Voice enabled."

    if any(w in q for w in ["mute jarvis", "silence", "be quiet", "quiet", "voice off", "turn off voice", "stop talking"]):
        data["mute"] = True
        _save(data)
        print("[JARVIS]: Voice muted. Say 'unmute jarvis' to re-enable.")
        return "Voice muted."

    # Plain "toggle voice" — flip current state
    data["mute"] = not currently_muted
    _save(data)
    if data["mute"]:
        print("[JARVIS]: Voice muted. Say 'unmute jarvis' to re-enable.")
        return "Voice muted."
    else:
        speak("Voice enabled.")
        return "Voice enabled."