# scripts/debug_command_registration.py
import pkgutil, importlib, sys
from pathlib import Path

# Map sys.platform to the project os_support tokens observed in your repo
PLATFORM_MAP = {
    "win32": "windows",
    "cygwin": "windows",
    "darwin": "macintosh",
    "linux": "linux",
}

current = PLATFORM_MAP.get(sys.platform, sys.platform)
print("Detected sys.platform:", sys.platform, "mapped to os token:", current)
print()

pkg_path = "Desktop_Assistant/commands"
for finder, name, ispkg in pkgutil.walk_packages([pkg_path], prefix="Desktop_Assistant.commands."):
    try:
        m = importlib.import_module(name)
    except Exception as e:
        print(name, "-> import failed:", type(e).__name__, str(e))
        continue

    meta = getattr(m, "get_metadata", lambda: None)()
    if not meta:
        print(name, "-> no metadata; loader may skip it")
        continue

    nm = (meta.get("name") or "<no-name>")
    aliases = meta.get("aliases") or []
    os_support = meta.get("os_support", None)

    reason = []
    # If os_support missing, many loaders treat it as cross-platform or as excluded.
    if os_support is None:
        reason.append("os_support=MISSING")
    else:
        # normalize tokens to lowercase strings
        tokens = [str(t).lower() for t in (os_support or [])]
        if current in tokens:
            reason.append(f"os_support includes {current}")
        else:
            reason.append(f"os_support does NOT include {current} ({tokens})")

    print(f"{name} -> name={nm} aliases={aliases} os_support={os_support} => {'; '.join(reason)}")
