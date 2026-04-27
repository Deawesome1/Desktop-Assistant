# Desktop_Assistant/commands/app_scanner/mac_scanner.py
"""
mac_scanner.py — macOS application scanner for JARVIS (uses centralized config_utils).
Implements the same public functions as the Windows scanner:
  - build_cache(force=False)
  - get_cache()
  - add_alias(app_name_lower, alias)
  - rescan()

This implementation mirrors the Windows scanner behavior:
- Progress bar seeded by a conservative pre-count of candidate .app bundles.
- Depth-limited scanning to avoid traversing entire volumes.
- Noise/skip lists to avoid indexing helper/framework bundles and system noise.
- Deduplication and alias preservation from existing cache.
- Resilient to permission errors and problematic bundles.
"""

from __future__ import annotations

import os
import sys
import time
import json
import glob
from pathlib import Path
from typing import Optional, List, Dict

from Desktop_Assistant.config_utils import config_path, read_config, write_config

# Config filenames (stored under Desktop_Assistant/config/)
CACHE_NAME = "app_cache.json"
CONFIG_NAME = "apps_config.json"

# Scan configuration
DEFAULT_SCAN_DIRS = [
    Path("/Applications"),
    Path("/System/Applications"),
    Path.home() / "Applications",
]

# Names and path fragments to skip (noise)
SKIP_DIR_NAMES = {
    ".Trash", "node_modules", "Library", "Caches", "PrivateFrameworks",
    "Frameworks", "PlugIns", "Versions", ".localized", "CoreServices",
}
SKIP_PATH_PREFIXES = {"/Volumes"}  # skip external volumes by default
SKIP_NAME_FRAGMENTS = [
    "helper", "plugin", "framework", "updater", "uninstall", "installer",
    "daemon", "agent", "service", "driver", "support", "sample", "example",
]

# Depth limit for scanning inside each top-level scan dir
MAX_DEPTH_DEFAULT = 3

# Progress printing frequency
PROGRESS_EVERY = 100

# -------------------------
# Utilities
# -------------------------
class ProgressBar:
    WIDTH = 40

    def __init__(self, total: int, label: str = "Progress"):
        self.total = max(total, 1)
        self.label = label
        self.current = 0
        self._draw(0, "")

    def update(self, current: int, suffix: str = ""):
        self.current = min(current, self.total)
        self._draw(self.current, suffix)

    def increment(self, suffix: str = ""):
        self.update(self.current + 1, suffix)

    def finish(self, message: str = "Done"):
        self._draw(self.total, message)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def _draw(self, current: int, suffix: str):
        pct = current / self.total
        filled = int(self.WIDTH * pct)
        bar = "█" * filled + "░" * (self.WIDTH - filled)
        pct_str = f"{int(pct * 100):3d}%"
        max_suffix = 30
        suffix_display = (suffix or "")[:max_suffix].ljust(max_suffix)
        line = f"\r  {self.label} [{bar}] {pct_str}  {suffix_display}"
        sys.stdout.write(line)
        sys.stdout.flush()


def _load_config() -> dict:
    defaults = {
        "allow_admin": False,
        "scan_on_startup": True,
        "extra_scan_paths": [],
        "max_depth": MAX_DEPTH_DEFAULT,
    }
    loaded = read_config(CONFIG_NAME, default={})
    if isinstance(loaded, dict):
        defaults.update(loaded)
    return defaults


def _normalize_name(raw: str) -> str:
    import re
    name = Path(raw).stem
    name = name.replace("_", " ").replace("-", " ")
    # remove common noise suffixes
    for noise in [" - Shortcut", " - Desktop", ".app"]:
        name = name.replace(noise, "")
    name = re.sub(r"\s*\((x64|x86|64.bit|32.bit|\d+)\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+\d+[\d\.\-]+.*$", "", name).strip()
    name = re.sub(r" {2,}", " ", name)
    return name.strip()


def _is_noisy_name(name: str) -> bool:
    ln = (name or "").lower()
    if not ln:
        return True
    if ln.endswith(".localized"):
        return True
    if ln.startswith("."):
        return True
    for frag in SKIP_NAME_FRAGMENTS:
        if frag in ln:
            return True
    # names that are just numbers or punctuation are noisy
    if all(c in "0123456789.-_ " for c in ln):
        return True
    return False


def _is_skippable_path(p: Path) -> bool:
    s = str(p)
    for prefix in SKIP_PATH_PREFIXES:
        if s.startswith(prefix):
            return True
    return False


# -------------------------
# Scanning helpers
# -------------------------
def _count_apps_in_dirs(dirs: List[Path], max_depth: int) -> int:
    """
    Count candidate .app directories under the provided dirs with a depth limit.
    Conservative count used to seed the progress bar.
    """
    count = 0
    for base in dirs:
        if not base.exists():
            continue
        for root, dirnames, _ in os.walk(base, topdown=True):
            try:
                rel = Path(root).relative_to(base)
                depth = len(rel.parts)
            except Exception:
                depth = 0
            if depth > max_depth:
                dirnames[:] = []
                continue
            if _is_skippable_path(Path(root)):
                dirnames[:] = []
                continue
            for d in list(dirnames):
                if d.lower().endswith(".app"):
                    count += 1
    return max(count, 1)


def _scan_directory(base: Path, seen_names: set, bar: ProgressBar, max_depth: int) -> List[dict]:
    """
    Depth-limited, safe scan for .app bundles under base.
    Uses os.scandir for speed and avoids following symlinks.
    """
    apps: List[dict] = []
    if not base.exists() or not base.is_dir():
        return apps

    scanned = 0

    def walk_dir(p: Path, depth: int):
        nonlocal scanned
        try:
            if _is_skippable_path(p):
                return
            with os.scandir(p) as it:
                for entry in it:
                    scanned += 1
                    if scanned % PROGRESS_EVERY == 0:
                        bar.update(bar.current, suffix=f"scanned {scanned}")
                    try:
                        name = entry.name
                        if _is_noisy_name(name):
                            continue
                        if name in SKIP_DIR_NAMES:
                            continue

                        # If it's a .app directory, evaluate it
                        if entry.is_dir(follow_symlinks=False) and name.lower().endswith(".app"):
                            item = Path(entry.path)
                            exec_dir = item / "Contents" / "MacOS"
                            exec_path_str = ""
                            try:
                                if exec_dir.exists() and exec_dir.is_dir():
                                    for child in exec_dir.iterdir():
                                        try:
                                            if child.is_file() and os.access(str(child), os.X_OK):
                                                exec_path_str = str(child)
                                                break
                                        except Exception:
                                            continue
                                if not exec_path_str:
                                    exec_path_str = str(item)
                            except Exception:
                                exec_path_str = str(item)

                            app_name = _normalize_name(item.stem)
                            if not app_name or len(app_name) < 2:
                                continue
                            key = app_name.lower()
                            if key in seen_names:
                                continue
                            seen_names.add(key)
                            apps.append({
                                "name": app_name,
                                "name_lower": key,
                                "path": exec_path_str,
                                "requires_admin": False,
                                "aliases": [],
                                "source": "filesystem",
                            })
                            bar.increment(suffix=app_name)
                            continue

                        # If directory and depth allows, descend (avoid symlinks)
                        if entry.is_dir(follow_symlinks=False) and depth < max_depth:
                            walk_dir(Path(entry.path), depth + 1)
                    except PermissionError:
                        continue
                    except Exception:
                        continue
        except PermissionError:
            return
        except Exception:
            return

    walk_dir(base, 0)
    return apps


def _dedup_apps(apps: List[dict]) -> List[dict]:
    """
    Deduplicate by name similarity. Prefer filesystem entries with executables.
    Mirrors the Windows dedup behavior but simplified for mac.
    """
    from difflib import SequenceMatcher
    import re

    def similarity(a: str, b: str) -> float:
        a = re.sub(r"[^a-z0-9 ]", "", a.lower())
        b = re.sub(r"[^a-z0-9 ]", "", b.lower())
        return SequenceMatcher(None, a, b).ratio()

    kept: List[dict] = []
    for app in apps:
        duplicate = False
        for existing in kept:
            if similarity(app["name_lower"], existing["name_lower"]) >= 0.88:
                # merge aliases
                for alias in app.get("aliases", []):
                    if alias not in existing.get("aliases", []):
                        existing.setdefault("aliases", []).append(alias)
                # prefer entries that point to an executable path (not bundle root)
                if app["path"] and existing["path"] and existing["path"].endswith(".app") and not app["path"].endswith(".app"):
                    kept.remove(existing)
                    kept.append(app)
                duplicate = True
                break
        if not duplicate:
            kept.append(app)
    return kept


# -------------------------
# Public API
# -------------------------
def build_cache(force: bool = False) -> dict:
    """
    Build or load the macOS app cache. Mirrors the Windows scanner flow:
    - load existing cache unless force=True
    - count candidates, show progress bar, scan directories
    - dedupe, preserve aliases, write cache
    """
    existing_aliases: Dict[str, List[str]] = {}

    existing = read_config(CACHE_NAME, default={})
    if existing and not force:
        for app in existing.get("apps", []):
            if app.get("aliases"):
                existing_aliases[app["name_lower"]] = app["aliases"]
        count = len(existing.get("apps", []))
        print(f"  Loaded app cache: {count} apps.\n")
        return existing

    cfg = _load_config()
    max_depth = int(cfg.get("max_depth", MAX_DEPTH_DEFAULT))
    extra_paths = cfg.get("extra_scan_paths", [])

    print("\n  Scanning macOS Applications...\n")

    # assemble scan dirs (user-configurable)
    scan_dirs: List[Path] = []
    for p in DEFAULT_SCAN_DIRS:
        if p.exists():
            scan_dirs.append(p)
    for ep in extra_paths:
        try:
            pp = Path(ep)
            if pp.exists():
                scan_dirs.append(pp)
        except Exception:
            continue

    # Pre-count candidate .app directories to seed progress bar
    print("  Counting candidate .app bundles...")
    total_candidates = _count_apps_in_dirs(scan_dirs, max_depth)
    total_candidates = max(total_candidates, 1)

    fs_bar = ProgressBar(total=total_candidates, label="Filesystem")
    seen_names: set = set()
    all_apps: List[dict] = []

    for directory in scan_dirs:
        found = _scan_directory(directory, seen_names, fs_bar, max_depth)
        all_apps.extend(found)

    fs_bar.finish(f"{len(all_apps)} apps found")

    # Preserve aliases from existing cache
    for app in all_apps:
        if app["name_lower"] in existing_aliases:
            app["aliases"] = existing_aliases[app["name_lower"]]

    # Deduplicate and sort
    all_apps = _dedup_apps(all_apps)
    all_apps.sort(key=lambda a: a["name_lower"])

    cache = {"app_count": len(all_apps), "apps": all_apps}
    write_config(CACHE_NAME, cache)

    print(f"\n  macOS scan complete: {len(all_apps)} apps indexed.\n")
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
