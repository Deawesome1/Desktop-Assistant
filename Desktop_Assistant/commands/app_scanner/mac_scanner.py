"""
mac_scanner.py — macOS application scanner for JARVIS

Scans:
 - /Applications
 - /System/Applications
 - ~/Applications

Detects .app bundles and extracts their executable paths.
Returns unified structure compatible with Windows/Linux scanners.
"""

import os
from pathlib import Path

# In-memory cache
_CACHE = {
    "app_count": 0,
    "apps": []
}


def _scan_directory(dir_path: Path) -> list[dict]:
    """Scan a directory for .app bundles and return normalized app entries."""
    results = []

    if not dir_path.exists():
        return results

    for item in dir_path.iterdir():
        if item.suffix.lower() == ".app" and item.is_dir():
            name = item.stem
            name_lower = name.lower()

            # macOS .app bundles contain the executable inside:
            # MyApp.app/Contents/MacOS/MyApp
            exec_path = item / "Contents" / "MacOS" / name
            exec_path_str = str(exec_path) if exec_path.exists() else str(item)

            results.append({
                "name": name,
                "name_lower": name_lower,
                "path": exec_path_str,
                "requires_admin": False,  # macOS apps rarely require admin to launch
                "aliases": [],
                "source": "filesystem"
            })

    return results


def build_cache(force: bool = False) -> dict:
    """Scan macOS application directories and build the unified cache."""
    global _CACHE

    if _CACHE["app_count"] > 0 and not force:
        return _CACHE

    print("\n  Scanning macOS Applications...")

    apps = []

    # Standard macOS application directories
    scan_dirs = [
        Path("/Applications"),
        Path("/System/Applications"),
        Path.home() / "Applications"
    ]

    for d in scan_dirs:
        apps.extend(_scan_directory(d))

    # Deduplicate by name_lower
    dedup = {}
    for app in apps:
        dedup[app["name_lower"]] = app

    apps = list(dedup.values())

    _CACHE = {
        "app_count": len(apps),
        "apps": apps
    }

    print(f"  macOS scan complete: {len(apps)} apps indexed.\n")

    return _CACHE


def get_cache() -> dict:
    """Return the current cache without rescanning."""
    return _CACHE


def add_alias(app_name_lower: str, alias: str) -> bool:
    """Add an alias to an app entry."""
    for app in _CACHE["apps"]:
        if app["name_lower"] == app_name_lower:
            if alias not in app["aliases"]:
                app["aliases"].append(alias)
            return True
    return False


def rescan() -> dict:
    """Force a full rescan."""
    return build_cache(force=True)
