"""
mac_impl.py — macOS application scanner for JARVIS (Omega)

Cleaned and made import‑surface‑compatible.
No deep imports. No project‑root assumptions.
"""

import os
from pathlib import Path

# In‑memory cache (macOS scanning is fast, so no disk cache needed)
CACHE_IN_MEMORY = None


# -------------------------------------------------------------------
# INTERNAL SCAN LOGIC
# -------------------------------------------------------------------

def _scan_macos() -> list[dict]:
    """
    Scan standard macOS application directories for .app bundles.
    Returns a list of app dictionaries with a uniform structure.
    """

    apps = []
    locations = [
        "/Applications",
        os.path.expanduser("~/Applications"),
    ]

    for base in locations:
        if not os.path.isdir(base):
            continue

        for item in os.listdir(base):
            if not item.endswith(".app"):
                continue

            full_path = os.path.join(base, item)
            name = item[:-4]  # strip ".app"

            apps.append({
                "name":           name,
                "name_lower":     name.lower(),
                "path":           full_path,
                "requires_admin": False,
                "aliases":        [],
                "source":         "filesystem",
            })

    apps.sort(key=lambda a: a["name_lower"])
    return apps


# -------------------------------------------------------------------
# PUBLIC API (matches Windows + Linux scanners)
# -------------------------------------------------------------------

def build_cache(force: bool = False) -> dict:
    """
    Build or return the in‑memory macOS app cache.
    """
    global CACHE_IN_MEMORY

    if CACHE_IN_MEMORY is not None and not force:
        return CACHE_IN_MEMORY

    apps = _scan_macos()

    CACHE_IN_MEMORY = {
        "app_count": len(apps),
        "apps": apps,
    }
    return CACHE_IN_MEMORY


def get_cache() -> dict:
    """
    Return the current cache (build if needed).
    """
    return build_cache(force=False)


def add_alias(app_name_lower: str, alias: str) -> bool:
    """
    Add an alias to an app in the in‑memory cache.
    """
    cache = get_cache()
    alias_lower = alias.lower().strip()

    for app in cache["apps"]:
        if app["name_lower"] == app_name_lower:
            if alias_lower not in [a.lower() for a in app["aliases"]]:
                app["aliases"].append(alias)
            return True

    return False


def rescan() -> dict:
    """
    Force a full rescan of macOS applications.
    """
    return build_cache(force=True)
