"""
imports.py — Central import surface for the Desktop Assistant (Omega)

This module provides ONE import point for:
 - Brain class
 - Speaker (OS-aware)
 - Listener (OS-aware)
 - OS key (from assistant’s own OS scanner)
 - CommandHub
 - CommandLoader
 - Standard utilities (re, json, urllib)
 - System helpers (clipboard, desktop path, etc.)
 - Unified OS-aware path resolution

Commands should NEVER import OS-specific modules directly.
Everything goes through this surface.
"""

# ------------------------------------------------------------
# Standard library re-exports
# ------------------------------------------------------------
import os
import re as _re
import json as _json
import urllib.request as _urllib_request
import urllib.parse as _urllib_parse
from typing import Any, Dict, List, Optional

# Expose clean names
re = _re
json = _json


class urllib:
    request = _urllib_request
    parse = _urllib_parse


# ------------------------------------------------------------
# Lazy import helpers
# ------------------------------------------------------------
import importlib


def _load(path: str):
    """Lazy import of a module by dotted path."""
    return importlib.import_module(path)


def _attr(path: str, name: str):
    """Load an attribute from a module."""
    return getattr(_load(path), name)


# ------------------------------------------------------------
# OS key (canonical)
# ------------------------------------------------------------
def os_key() -> str:
    """
    Return the assistant's normalized OS key:
        "windows", "macintosh", "linux"
    """
    value = _attr("Desktop_Assistant.commands.os_scanner", "current_os")
    return value() if callable(value) else value


# ------------------------------------------------------------
# Brain
# ------------------------------------------------------------
def Brain():
    return _attr("Desktop_Assistant.brain.engine.brain", "Brain")


# ------------------------------------------------------------
# Speaker / Listener (OS-aware)
# ------------------------------------------------------------
def speak(text: str) -> None:
    """OS-aware speak() wrapper."""
    try:
        _speak = _attr("Desktop_Assistant.brain.engine.speaker", "speak")
        _speak(text)
    except Exception:
        pass  # Silent fail for robustness


def listen_once(timeout: int = 8) -> str:
    """OS-aware single-shot listener."""
    try:
        _listen = _attr("Desktop_Assistant.brain.engine.listener", "listen_once")
        return _listen(timeout=timeout)
    except Exception:
        return ""


# ------------------------------------------------------------
# CommandHub / Loader
# ------------------------------------------------------------
def CommandHub():
    return _attr("Desktop_Assistant.commands.command_hub", "CommandHub")


def CommandLoader():
    return _attr("Desktop_Assistant.brain.loader", "CommandLoader")


# ------------------------------------------------------------
# OS-AWARE PATH HELPERS (Unified, Self-Healing)
# ------------------------------------------------------------

def _ensure_dir(path: str) -> str:
    """Create directory if missing, return path."""
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except Exception:
        # Fallback if Desktop/Documents/etc. cannot be created
        fallback = os.path.join(os.path.expanduser("~"), "Omega_Fallback")
        os.makedirs(fallback, exist_ok=True)
        return fallback


def get_desktop() -> str:
    """
    Return a guaranteed-valid Desktop path on Windows, macOS, or Linux.
    Uses assistant OS key (not platform.system).
    Auto-creates the folder if missing.
    """
    home = os.path.expanduser("~")
    os_name = os_key()

    # Windows + macOS → same Desktop path
    if os_name in ("windows", "macintosh"):
        return _ensure_dir(os.path.join(home, "Desktop"))

    # Linux → XDG-aware
    xdg_config = os.path.join(home, ".config", "user-dirs.dirs")
    desktop = os.path.join(home, "Desktop")

    if os.path.exists(xdg_config):
        try:
            with open(xdg_config, "r", encoding="utf-8") as f:
                for line in f:
                    if "XDG_DESKTOP_DIR" in line:
                        path = line.split("=")[1].strip().strip('"')
                        path = path.replace("$HOME", home)
                        desktop = path
                        break
        except Exception:
            pass

    return _ensure_dir(desktop)


# ------------------------------------------------------------
# Clipboard helpers (OS-aware via pyperclip)
# ------------------------------------------------------------

def get_clipboard() -> str:
    """Return clipboard contents or raise RuntimeError."""
    try:
        import pyperclip
        return pyperclip.paste() or ""
    except Exception as e:
        raise RuntimeError("Clipboard backend not available") from e


def clear_clipboard() -> None:
    """Clear clipboard or raise RuntimeError."""
    try:
        import pyperclip
        pyperclip.copy("")
    except Exception as e:
        raise RuntimeError("Clipboard backend not available") from e


# ------------------------------------------------------------
# Compatibility Imports class (Unified)
# ------------------------------------------------------------

class Imports:
    """Compatibility wrapper for older code."""

    # Standard libs
    re = re
    json = json
    urllib = urllib

    # Core
    def Brain(self):
        return Brain()

    def speak(self, text: str):
        return speak(text)

    def listen_once(self, timeout: int = 8):
        return listen_once(timeout)

    def os_key(self):
        return os_key()

    def CommandHub(self):
        return CommandHub()

    def CommandLoader(self):
        return CommandLoader()

    # System helpers
    def get_desktop(self):
        return get_desktop()

    def get_clipboard(self):
        return get_clipboard()

    def clear_clipboard(self):
        return clear_clipboard()
