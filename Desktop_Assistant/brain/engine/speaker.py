# Desktop_Assistant/brain/engine/speaker.py
from __future__ import annotations
import subprocess, sys, importlib, traceback

# Try to import the exact module you tested earlier.
# Use importlib.import_module to avoid subtle package import issues.
_speak = None
_listen_once = None

try:
    _mod = importlib.import_module("Desktop_Assistant.bot.speaker.speaker")
    _speak = getattr(_mod, "speak", None)
    _listen_once = getattr(_mod, "listen_once", None)
except Exception:
    # keep _speak as None so fallback is used
    traceback.print_exc()

def speak(text: str, block: bool = False) -> None:
    """
    Primary speak function used by the app.
    Delegates to Desktop_Assistant.bot.speaker.speaker.speak when available,
    otherwise falls back to macOS `say` or a printed fallback.
    """
    if not text:
        return
    # Prefer the real implementation if it is callable
    if callable(_speak):
        try:
            return _speak(text, block=block)
        except Exception:
            # If the real implementation fails, fall through to fallback
            traceback.print_exc()
    # Fallback: use macOS `say` if available
    try:
        subprocess.run(["say", text], check=False)
    except Exception:
        try:
            print(f"JARVIS (TTS fallback): {text}")
        except Exception:
            pass

def listen_once(timeout: int = 8) -> str:
    """
    Optional listen helper. Delegates to the underlying implementation if present,
    otherwise falls back to a simple stdin prompt.
    """
    if callable(_listen_once):
        try:
            return _listen_once(timeout=timeout)
        except Exception:
            traceback.print_exc()
    try:
        sys.stdout.write("You (type): ")
        sys.stdout.flush()
        return sys.stdin.readline().strip()
    except Exception:
        return ""