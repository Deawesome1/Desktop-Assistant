# Desktop_Assistant/brain/engine/speaker.py
"""
Cross-platform speaker backend for JARVIS.

Behavior:
- macOS: uses the native `say` command (no extra Python deps).
- Linux: tries `spd-say`, then `espeak`, then falls back to pyttsx3 if available.
- Windows: tries pyttsx3 first, then win32com (pywin32) if available.
- If no TTS backend is available, falls back to printing the text.
This module never imports Windows-only modules unguarded; ImportError is handled.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from typing import Optional

try:
    from Desktop_Assistant.boot.path_hub import OS_KEY
except Exception:
    # fallback to platform detection if path_hub not available
    import platform as _platform
    _sys = _platform.system().lower()
    if "darwin" in _sys:
        OS_KEY = "macintosh"
    elif "windows" in _sys:
        OS_KEY = "windows"
    else:
        OS_KEY = "linux"


def _run_cmd(cmd: str) -> bool:
    try:
        subprocess.run(shlex.split(cmd), check=False)
        return True
    except Exception:
        return False


def _say_mac(text: str) -> bool:
    try:
        # Use the native macOS `say` command
        subprocess.run(["say", text], check=False)
        return True
    except Exception:
        return False


def _say_linux(text: str) -> bool:
    # Try spd-say
    if _run_cmd(f"spd-say {shlex.quote(text)}"):
        return True
    # Try espeak
    if _run_cmd(f"espeak {shlex.quote(text)}"):
        return True
    # Try pyttsx3 as a Python fallback
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception:
        return False


def _say_windows(text: str) -> bool:
    # Prefer pyttsx3 (pure Python, cross-platform)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception:
        pass

    # Try win32com (pywin32) if available
    try:
        # Import guarded to avoid ImportError on non-Windows platforms
        import win32com.client  # type: ignore
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Speak(text)
        return True
    except Exception:
        return False


def speak(text: str, block: bool = False) -> None:
    """
    Speak the provided text using the best available backend.
    block parameter is accepted for API compatibility; backends used here are blocking.
    """
    if not text:
        return

    ok = False
    if OS_KEY == "macintosh":
        ok = _say_mac(text)
    elif OS_KEY == "linux":
        ok = _say_linux(text)
    elif OS_KEY == "windows":
        ok = _say_windows(text)
    else:
        # unknown OS: try pyttsx3 then fallback to print
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            ok = True
        except Exception:
            ok = False

    if not ok:
        # Final fallback: print to stdout so user still sees the message
        try:
            print(f"JARVIS (TTS fallback): {text}")
        except Exception:
            pass
