"""
system_info_windows.py — JARVIS Command (Windows)
Report CPU, RAM, disk, uptime, and battery (if present).
"""

from Desktop_Assistant import imports as I
import platform
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "system_info"
COMMAND_ALIASES: List[str] = [
    "system info", "system status", "cpu", "ram", "memory",
    "disk", "storage", "uptime", "battery"
]
COMMAND_DESCRIPTION: str = "Reports system information on Windows."
COMMAND_OS_SUPPORT: List[str] = ["windows"]
COMMAND_CATEGORY: str = "system"
COMMAND_REQUIRES_INTERNET: bool = False
COMMAND_REQUIRES_ADMIN: bool = False


# ---------------------------------------------------------------------------
# Metadata API
# ---------------------------------------------------------------------------

def get_metadata() -> Dict[str, Any]:
    return {
        "name": COMMAND_NAME,
        "aliases": COMMAND_ALIASES,
        "description": COMMAND_DESCRIPTION,
        "os_support": COMMAND_OS_SUPPORT,
        "category": COMMAND_CATEGORY,
        "requires_internet": COMMAND_REQUIRES_INTERNET,
        "requires_admin": COMMAND_REQUIRES_ADMIN,
    }


def is_supported_on_os(os_key: str) -> bool:
    return os_key == "windows"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cpu() -> str:
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        freq = psutil.cpu_freq()
        cores = psutil.cpu_count(logical=False)
        freq_str = f" at {freq.current:.0f} MHz" if freq else ""
        return f"CPU at {cpu}%{freq_str}, {cores} cores."
    except Exception as e:
        return f"Couldn't read CPU: {e}"


def _ram() -> str:
    try:
        import psutil
        mem = psutil.virtual_memory()
        used = mem.used / (1024 ** 3)
        total = mem.total / (1024 ** 3)
        return f"RAM: {used:.1f} of {total:.1f} GB used ({mem.percent}%)."
    except Exception as e:
        return f"Couldn't read RAM: {e}"


def _disk() -> str:
    try:
        import psutil
        disk = psutil.disk_usage("C:\\")
        free = disk.free / (1024 ** 3)
        total = disk.total / (1024 ** 3)
        return f"Disk: {free:.0f} GB free of {total:.0f} GB ({disk.percent}% used)."
    except Exception as e:
        return f"Couldn't read disk: {e}"


def _battery() -> Optional[str]:
    try:
        import psutil
        batt = psutil.sensors_battery()
        if batt is None:
            return None
        status = "charging" if batt.power_plugged else "discharging"
        return f"Battery at {int(batt.percent)}%, {status}."
    except Exception:
        return None


def _uptime() -> str:
    try:
        import psutil, time
        boot = psutil.boot_time()
        uptime = int(time.time() - boot)
        h, r = divmod(uptime, 3600)
        m, _ = divmod(r, 60)
        return f"Uptime: {h}h {m}m."
    except Exception:
        return ""


def _full_summary() -> str:
    parts = [_cpu(), _ram(), _disk(), _uptime()]
    batt = _battery()
    if batt:
        parts.append(batt)
    return " ".join(parts)


SPECIFIC_KEYWORDS = {
    "cpu": _cpu,
    "ram": _ram,
    "memory": _ram,
    "disk": _disk,
    "storage": _disk,
    "uptime": _uptime,
    "battery": _battery,
}


# ---------------------------------------------------------------------------
# Public run() entrypoint
# ---------------------------------------------------------------------------

def run(
    brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    try:
        import psutil  # noqa
    except ImportError:
        return {
            "success": False,
            "message": "System info requires psutil. Run pip install psutil.",
            "data": {"error": "missing_dependency"},
        }

    q = user_text.lower()

    # Specific request
    for keyword, fn in SPECIFIC_KEYWORDS.items():
        if keyword in q:
            if keyword == "battery":
                result = _battery()
                msg = result if result else "No battery detected. You're on a desktop."
            else:
                msg = fn()

            brain.event("task_success")
            brain.remember("system_info_queries", keyword)

            return {
                "success": True,
                "message": msg,
                "data": {"type": keyword, "result": msg},
            }

    # Full summary
    summary = _full_summary()

    brain.event("task_success")
    brain.remember("system_info_queries", "full_summary")

    return {
        "success": True,
        "message": summary,
        "data": {"type": "full_summary", "result": summary},
    }
