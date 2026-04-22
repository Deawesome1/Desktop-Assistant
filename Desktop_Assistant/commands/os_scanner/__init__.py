"""
os_scanner — Unified OS detection + OS‑specific app scanner loader.

This module provides:
    - get_os_key()  → returns "windows", "macintosh", or "linux"
    - current_os    → cached OS key
    - get_scanner() → returns the correct OS‑specific scanner module
"""

import platform
import importlib


# -------------------------------------------------------------------
# OS DETECTION
# -------------------------------------------------------------------

def get_os_key() -> str:
    """
    Normalize platform.system() into one of:
        - "windows"
        - "macintosh"
        - "linux"
    """
    name = platform.system().lower()

    if "windows" in name:
        return "windows"

    if "darwin" in name or "mac" in name:
        return "macintosh"

    return "linux"


# Cached OS key
current_os = get_os_key()


# -------------------------------------------------------------------
# SCANNER LOADER
# -------------------------------------------------------------------

def get_scanner():
    """
    Dynamically load the correct OS‑specific scanner module.

    Returns a module with:
        - build_cache()
        - get_cache()
        - add_alias()
        - rescan()
    """

    if current_os == "windows":
        return importlib.import_module(
            "Desktop_Assistant.commands.os_specific.windows.windows"
        )

    if current_os == "macintosh":
        return importlib.import_module(
            "Desktop_Assistant.commands.os_specific.macintosh.mac_impl"
        )

    # Default: Linux
    return importlib.import_module(
        "Desktop_Assistant.commands.os_specific.linux.linux_impl"
    )
