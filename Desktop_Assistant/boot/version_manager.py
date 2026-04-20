# boot/version_manager.py

from pathlib import Path
import platform
import sys

VERSION_FILE = Path(".jarvis_version")
JARVIS_VERSION = "0.1.0"  # update as you release


def load_version() -> str | None:
    if not VERSION_FILE.exists():
        return None
    return VERSION_FILE.read_text(encoding="utf-8").strip() or None


def record_version():
    info = {
        "jarvis_version": JARVIS_VERSION,
        "python": f"{sys.version_info[0]}.{sys.version_info[1]}",
        "os": platform.platform(),
    }
    text = "\n".join(f"{k}={v}" for k, v in info.items())
    VERSION_FILE.write_text(text, encoding="utf-8")
    print(f"\n✓ Version recorded in {VERSION_FILE}")
