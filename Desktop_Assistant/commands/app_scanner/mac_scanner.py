"""
mac_impl.py — macOS application scanner for JARVIS.

Scans /Applications and ~/Applications for .app bundles.
Returns the same structure as the Windows implementation.
"""

import os
from pathlib import Path

CACHE_IN_MEMORY = None  # simple in‑memory cache only


def _scan_macos() -> list[dict]:
    apps: list[dict] = []
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
            name = item[:-4]  # strip .app
            name_lower = name.lower()

            apps.append({
                "name":           name,
                "name_lower":     name_lower,
                "path":           full_path,
                "requires_admin": False,
                "aliases":        [],
                "source":         "filesystem",
            })

    apps.sort(key=lambda a: a["name_lower"])
    return apps


def build_cache(force: bool = False) -> dict:
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
    return build_cache(force=False)


def add_alias(app_name_lower: str, alias: str) -> bool:
    cache = get_cache()
    alias_lower = alias.lower().strip()

    for app in cache["apps"]:
        if app["name_lower"] == app_name_lower:
            if alias_lower not in [a.lower() for a in app["aliases"]]:
                app["aliases"].append(alias)
            return True

    return False


def rescan() -> dict:
    return build_cache(force=True)
