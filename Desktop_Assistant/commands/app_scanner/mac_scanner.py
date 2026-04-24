# Desktop_Assistant/commands/app_scanner/mac_scanner.py
"""
mac_scanner.py — macOS application scanner for JARVIS (uses centralized config_utils).
Implements the same public functions as the Windows scanner:
  - build_cache(force=False)
  - get_cache()
  - add_alias(app_name_lower, alias)
  - rescan()
"""

from __future__ import annotations

import os
import glob
from pathlib import Path
from typing import Optional

from Desktop_Assistant.config_utils import config_path, read_config, write_config

CACHE_NAME = "app_cache.json"


def _normalize_name(raw: str) -> str:
    name = Path(raw).stem
    name = name.replace("_", " ").replace("-", " ")
    return name.strip()


def _scan_directory(directory: Path) -> list[dict]:
    results = []
    if not directory.exists():
        return results

    # Find .app bundles recursively
    for filepath in glob.glob(str(directory / "**" / "*.app"), recursive=True):
        item = Path(filepath)
        name = _normalize_name(item.stem)
        if not name:
            continue
        # Attempt to find the executable inside the bundle
        exec_path = item / "Contents" / "MacOS" / name
        exec_path_str = str(exec_path) if exec_path.exists() else str(item)
        results.append({
            "name": name,
            "name_lower": name.lower(),
            "path": exec_path_str,
            "requires_admin": False,
            "aliases": [],
            "source": "filesystem",
        })
    return results


def build_cache(force: bool = False) -> dict:
    existing = read_config(CACHE_NAME, default={})
    if existing and not force:
        return existing

    print("\n  Scanning macOS Applications...")

    apps = []
    scan_dirs = [
        Path("/Applications"),
        Path("/System/Applications"),
        Path.home() / "Applications",
    ]

    for d in scan_dirs:
        apps.extend(_scan_directory(d))

    # Deduplicate by name_lower (simple last-wins)
    dedup = {}
    for app in apps:
        dedup[app["name_lower"]] = app

    apps = list(dedup.values())
    apps.sort(key=lambda a: a["name_lower"])

    cache = {"app_count": len(apps), "apps": apps}
    write_config(CACHE_NAME, cache)

    print(f"  macOS scan complete: {len(apps)} apps indexed.\n")
    return cache


def get_cache() -> dict:
    existing = read_config(CACHE_NAME, default=None)
    if not existing:
        return build_cache(force=True)
    return existing


def add_alias(app_name_lower: str, alias: str) -> bool:
    cache = get_cache()
    alias_lower = alias.lower().strip()
    for app in cache.get("apps", []):
        if app["name_lower"] == app_name_lower:
            if alias_lower not in [a.lower() for a in app.get("aliases", [])]:
                app.setdefault("aliases", []).append(alias)
                write_config(CACHE_NAME, cache)
            return True
    return False


def rescan() -> dict:
    return build_cache(force=True)
