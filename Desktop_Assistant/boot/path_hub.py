# Desktop_Assistant/boot/path_hub.py
"""
Centralized path hub for Desktop Assistant.

Responsibilities
- Provide a single source of truth for PROJECT_ROOT and current OS key.
- Provide safe path joining that treats absolute parts (including Windows drive-letter strings)
  as authoritative so cross-platform literals do not get concatenated into invalid paths.
- Expose common repo paths (config, requirements, venv layout) and small helpers used across the codebase.
- Keep no side effects at import time.
"""

from __future__ import annotations

import re
import platform
from pathlib import Path
from typing import Optional, Union, Dict

# ---------------------------------------------------------------------
# Basic environment and OS key
# ---------------------------------------------------------------------
# PROJECT_ROOT resolves to repository root (two levels above this file:
# Desktop_Assistant/boot/path_hub.py -> Desktop_Assistant/boot -> Desktop_Assistant -> repo root)
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

_sys = platform.system().lower()
if "windows" in _sys:
    OS_KEY = "windows"
elif "darwin" in _sys:
    OS_KEY = "macintosh"
else:
    OS_KEY = "linux"

# Recognize Windows absolute path patterns like "C:\..." or "A:\..."
_WINDOWS_ABS_RE = re.compile(r"^[A-Za-z]:\\")  # backslash style
_WINDOWS_ABS_RE_ALT = re.compile(r"^[A-Za-z]:/")  # forward slash style (defensive)


# ---------------------------------------------------------------------
# Safe join and normalization helpers
# ---------------------------------------------------------------------
def looks_like_windows_abs(s: str) -> bool:
    if not isinstance(s, str) or not s:
        return False
    return bool(_WINDOWS_ABS_RE.match(s) or _WINDOWS_ABS_RE_ALT.match(s))


def safe_join(base: Union[str, Path], *parts: str) -> Path:
    """
    Join path parts but treat any absolute part as authoritative.
    Also treat Windows-style drive-letter strings as absolute even on non-Windows hosts.

    Examples:
      safe_join(PROJECT_ROOT, "Desktop_Assistant", "config", "os_routing.json")
      safe_join(PROJECT_ROOT, "A:\\GitHub\\Desktop-Assistant\\Desktop_Assistant\\config\\os_routing.json")
    """
    cur = Path(base)
    for p in parts:
        if not p:
            continue
        # If the part looks like a Windows absolute path, return it as Path (do not join)
        if isinstance(p, str) and looks_like_windows_abs(p):
            return Path(p)
        p_path = Path(p)
        if p_path.is_absolute():
            cur = p_path
        else:
            cur = cur / p_path
    try:
        return cur.resolve()
    except Exception:
        # best-effort: return normalized path even if resolution fails
        return cur


def normalize_path(p: Union[str, Path]) -> Path:
    """
    Normalize and resolve a path-like value. Accepts Windows-style drive strings.
    """
    if isinstance(p, str) and looks_like_windows_abs(p):
        return Path(p)
    try:
        return Path(p).resolve()
    except Exception:
        return Path(p)


# ---------------------------------------------------------------------
# Common repo paths and helpers
# ---------------------------------------------------------------------
def repo_path(*parts: str) -> Path:
    """Return a path under the repository root."""
    return safe_join(PROJECT_ROOT, *parts)


def package_path(*parts: str) -> Path:
    """Return a path under the Desktop_Assistant package directory."""
    return safe_join(PROJECT_ROOT, "Desktop_Assistant", *parts)


def config_path(filename: str) -> Path:
    """Return the canonical config file path inside the package config directory."""
    return package_path("config", filename)


def requirements_dir() -> Path:
    """Return the Desktop_Assistant/requirements directory path."""
    return package_path("requirements")


def venv_paths(venv_root: Union[str, Path]) -> Dict[str, str]:
    """
    Return common venv executable paths for the detected OS.
    venv_root should be the path to the virtualenv directory.
    """
    v = Path(venv_root)
    if OS_KEY == "windows":
        return {
            "python": str(v / "Scripts" / "python.exe"),
            "pip": str(v / "Scripts" / "pip.exe"),
            "activate": str(v / "Scripts" / "activate"),
        }
    else:
        return {
            "python": str(v / "bin" / "python"),
            "pip": str(v / "bin" / "pip"),
            "activate": str(v / "bin" / "activate"),
        }


def default_brain_config() -> Path:
    """
    Return the default brain.json path the Brain should use when no explicit config_path is provided.
    This mirrors the previous behavior but uses safe resolution.
    """
    # prefer Desktop_Assistant/config/brain.json
    p = package_path("config", "brain.json")
    if p.exists():
        return p
    # fallback to repo-root config/brain.json
    alt = repo_path("config", "brain.json")
    return alt


def os_routing_config() -> Path:
    """
    Return the canonical os_routing.json path. Prefer package config, then repo config.
    """
    p = package_path("config", "os_routing.json")
    if p.exists():
        return p
    alt = repo_path("config", "os_routing.json")
    return alt


# ---------------------------------------------------------------------
# Small convenience utilities
# ---------------------------------------------------------------------
def get_user_desktop() -> Path:
    """Return the current user's Desktop path in a cross-platform way."""
    home = Path.home()
    if OS_KEY == "windows":
        return safe_join(home, "Desktop")
    if OS_KEY == "macintosh":
        return safe_join(home, "Desktop")
    return safe_join(home, "Desktop")


def get_downloads_dir() -> Path:
    """Return the current user's Downloads directory (best-effort)."""
    home = Path.home()
    if OS_KEY == "windows":
        return safe_join(home, "Downloads")
    if OS_KEY == "macintosh":
        return safe_join(home, "Downloads")
    return safe_join(home, "Downloads")
