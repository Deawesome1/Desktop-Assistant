"""
bot/speaker.py — JARVIS text-to-speech module.

Engine priority:
  1. edge-tts  — Microsoft neural voices, most natural (pip install edge-tts)
  2. pyttsx3   — offline fallback
  3. print     — muted mode or no TTS installed

Set "mute": true in config/voice.json to disable speech entirely.
Set "engine": "edge-tts" or "pyttsx3" to force a specific engine.
"""

import os
import json
import asyncio
import tempfile

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "voice.json")


def _load_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _get_tts_hints() -> dict:
    """Pull TTS hints from active personality profile."""
    try:
        from bot.personality.engine import _active
        return _active().get("tts_hints", {})
    except Exception:
        return {}


def _speak_edge_tts(text: str, voice: str, rate: int):
    """Speak using edge-tts neural voice (async)."""
    try:
        import edge_tts
        import pygame

        # Build SSML rate string
        rate_str = f"+{rate - 150}%" if rate >= 150 else f"-{150 - rate}%"

        async def _run():
            communicate = edge_tts.Communicate(text, voice, rate=rate_str)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp = f.name
            await communicate.save(tmp)
            return tmp

        tmp = asyncio.run(_run())

        pygame.mixer.init()
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.quit()

        try:
            os.unlink(tmp)
        except Exception:
            pass

    except ImportError:
        raise ImportError("edge-tts or pygame not installed")
    except Exception as e:
        raise RuntimeError(f"edge-tts failed: {e}")


def speak(text: str):
    """
    Speak text using the configured TTS engine.
    Set "mute": true in voice.json to print instead.
    """
    config = _load_config()

    if config.get("mute", False):
        print(f"[JARVIS]: {text}")
        return

    hints  = _get_tts_hints()
    engine = config.get("engine", hints.get("preferred_engine", "pyttsx3"))
    rate   = config.get("rate", hints.get("rate", 172))

    # ── edge-tts ──────────────────────────────────────────────────────────────
    if engine == "edge-tts":
        voice = config.get("edge_tts_voice",
                           hints.get("edge_tts_voice", "en-US-GuyNeural"))
        try:
            _speak_edge_tts(text, voice, rate)
            return
        except ImportError:
            pass  # Fall through to pyttsx3
        except Exception as e:
            print(f"[JARVIS — edge-tts error ({e})]: {text}")
            return

    # ── pyttsx3 ───────────────────────────────────────────────────────────────
    try:
        import pyttsx3
        engine_obj = pyttsx3.init()
        engine_obj.setProperty("rate",   rate)
        engine_obj.setProperty("volume", config.get("volume", 0.95))
        voices = engine_obj.getProperty("voices")
        if voices:
            idx = config.get("voice_index", 0)
            if idx >= len(voices):
                idx = 0
            engine_obj.setProperty("voice", voices[idx].id)
        engine_obj.say(text)
        engine_obj.runAndWait()
        engine_obj.stop()
    except ImportError:
        print(f"[JARVIS — pyttsx3 not installed]: {text}")
    except Exception as e:
        print(f"[JARVIS — TTS error ({e})]: {text}")


def reload_voice():
    """No-op — config re-read on every speak() call."""
    pass


def get_response(key: str) -> str:
    """
    Retrieve a system response string.
    Personality engine checked first, falls back to voice.json.
    """
    try:
        from bot.personality.engine import get_response as pr
        result = pr(key)
        if result and result != key:
            return result
    except Exception:
        pass
    config = _load_config()
    return config.get("responses", {}).get(key, key)