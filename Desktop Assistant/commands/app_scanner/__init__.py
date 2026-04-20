"""
Unified app scanner for JARVIS.

Public API (same on all platforms):
    build_cache(force: bool = False) -> dict
    get_cache() -> dict
    add_alias(app_name_lower: str, alias: str) -> bool
    rescan() -> dict

All return a dict shaped like:
{
    "app_count": int,
    "apps": [
        {
            "name": "Google Chrome",
            "name_lower": "google chrome",
            "path": "/path/to/app",
            "requires_admin": bool,
            "aliases": [str, ...],
            "source": "filesystem" | "registry"
        },
        ...
    ]
}
"""

import platform

OS_NAME = platform.system().lower()

if OS_NAME == "windows":
    from windows_scanner import (
        build_cache,
        get_cache,
        add_alias,
        rescan,
    )
elif OS_NAME == "darwin":
    from mac_scanner import (
        build_cache,
        get_cache,
        add_alias,
        rescan,
    )
elif OS_NAME == "linux":
    from linux_scanner import (
        build_cache,
        get_cache,
        add_alias,
        rescan,
    )
else:
    # Fallback: empty implementations so imports never fail
    def build_cache(force: bool = False) -> dict:
        return {"app_count": 0, "apps": []}

    def get_cache() -> dict:
        return {"app_count": 0, "apps": []}

    def add_alias(app_name_lower: str, alias: str) -> bool:
        return False

    def rescan() -> dict:
        return {"app_count": 0, "apps": []}
