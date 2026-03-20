"""
speaker.py — JARVIS text-to-speech module.
Loads voice settings from config/voice.json and speaks responses.
"""

import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "voice.json")


def _load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def speak(text: str):
    """
    Speak the given text using the configured TTS engine.
    Set "mute": true in config/voice.json to disable speech (prints instead).
    """
    config = _load_config()

    if config.get("mute", False):
        print(f"[JARVIS]: {text}")
        return

    if config.get("engine", "pyttsx3") != "pyttsx3":
        print(f"[JARVIS]: {text}")
        return

    try:
        import pyttsx3

        engine = pyttsx3.init()

        engine.setProperty("rate",   config.get("rate",   185))
        engine.setProperty("volume", config.get("volume", 1.0))

        voices = engine.getProperty("voices")
        if voices:
            voice_index = config.get("voice_index", 0)
            if voice_index >= len(voices):
                voice_index = 0
            engine.setProperty("voice", voices[voice_index].id)

        engine.say(text)
        engine.runAndWait()
        engine.stop()

    except ImportError:
        print(f"[JARVIS — pyttsx3 not installed]: {text}")
    except Exception as e:
        print(f"[JARVIS — TTS error ({e})]: {text}")


def reload_voice():
    """No-op — kept for compatibility. Config is re-read on every speak() call."""
    pass


def get_response(key: str) -> str:
    """
    Retrieve a response string for a system event.
    Personality engine is checked first; falls back to voice.json.
    """
    try:
        from bot.personality.engine import get_response as personality_response
        result = personality_response(key)
        if result and result != key:
            return result
    except Exception:
        pass
    config = _load_config()
    return config.get("responses", {}).get(key, key)