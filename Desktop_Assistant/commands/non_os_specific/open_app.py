# Desktop_Assistant/commands/non_os_specific/open_app.py
"""
Open / Launch command.

Usage examples:
  - "open vscode"
  - "launch spotify"
  - "start rocket league"

This command looks up the app cache (app_cache.json) and uses the centralized
launcher to start the selected application. It supports exact, alias,
substring and fuzzy matching (difflib).
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from difflib import SequenceMatcher, get_close_matches

from Desktop_Assistant.commands.app_scanner import get_cache
from Desktop_Assistant.launcher import launch_app

logger = logging.getLogger("jarvis.command.open_app")

def get_metadata() -> Dict[str, Any]:
    # Note: 'entry' points to the callable name the loader should use.
    return {
        "name": "open_app",
        "aliases": ["open", "launch", "start"],
        "category": "system",
        "timeout": 15.0,
        "speak": False,
        "os_support": ["windows", "macintosh", "linux"],
        "entry": "invoke",
    }

def _normalize_query(text: str) -> str:
    return text.strip().lower()

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def _find_best_match(query: str, cache: dict) -> Optional[dict]:
    q = query.lower().strip()
    apps = cache.get("apps", []) if cache else []

    # 1) exact name_lower
    for app in apps:
        if app.get("name_lower") == q:
            return app

    # 2) alias exact
    for app in apps:
        for a in app.get("aliases", []):
            if a and a.lower().strip() == q:
                return app

    # 3) substring
    for app in apps:
        if q and q in (app.get("name_lower") or ""):
            return app

    # 4) fuzzy
    names = [a.get("name_lower", "") for a in apps]
    close = get_close_matches(q, names, n=5, cutoff=0.6)
    if close:
        best_name = max(close, key=lambda n: _similarity(n, q))
        for app in apps:
            if app.get("name_lower") == best_name:
                return app

    return None

def invoke(brain, user_text: str) -> Dict[str, Any]:
    """
    Expected return shape:
      {"success": bool, "message": str, "data": {...}}
    """
    try:
        text = (user_text or "").strip()
        lowered = text.lower()
        for prefix in ("open ", "launch ", "start "):
            if lowered.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        if not text:
            return {"success": False, "message": "Which app would you like me to open?", "data": {}}

        query = _normalize_query(text)
        cache = get_cache() or {"apps": []}
        app = _find_best_match(query, cache)

        if not app:
            names = [a.get("name") for a in cache.get("apps", [])][:10]
            return {
                "success": False,
                "message": f"I couldn't find an app matching '{text}'. Try a different name.",
                "data": {"suggestions": names},
            }

        path = app.get("path") or ""
        requires_admin = bool(app.get("requires_admin", False))

        res = launch_app(path, requires_admin=requires_admin)
        if res.get("ok"):
            return {
                "success": True,
                "message": f"Launching {app.get('name')}.",
                "data": {"app": app, "method": res.get("method")},
            }

        return {
            "success": False,
            "message": f"Failed to launch {app.get('name')}.",
            "data": {"app": app, "error": res.get("error")},
        }

    except Exception as exc:
        logger.exception("open_app command failed: %s", exc)
        return {"success": False, "message": "An error occurred while trying to open the app.", "data": {"error": str(exc)}}
