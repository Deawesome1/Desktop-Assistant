"""
commands/system_info.py — Cross-platform system status.
Reports CPU, RAM, disk, GPU temp (if available), uptime.
Battery is only reported if one is detected (laptops/UPS).
"""
import platform
from bot.speaker import speak


def _cpu() -> str:
    try:
        import psutil
        cpu   = psutil.cpu_percent(interval=1)
        freq  = psutil.cpu_freq()
        cores = psutil.cpu_count(logical=False)
        freq_str = f" at {freq.current:.0f} MHz" if freq else ""
        return f"CPU at {cpu} percent{freq_str}, {cores} cores."
    except Exception as e:
        return f"Couldn't read CPU: {e}"


def _ram() -> str:
    try:
        import psutil
        mem   = psutil.virtual_memory()
        used  = mem.used  / (1024 ** 3)
        total = mem.total / (1024 ** 3)
        return f"RAM: {used:.1f} of {total:.1f} GB used ({mem.percent}%)."
    except Exception as e:
        return f"Couldn't read RAM: {e}"


def _disk() -> str:
    try:
        import psutil, sys
        root = "C:\\" if sys.platform == "win32" else "/"
        disk  = psutil.disk_usage(root)
        free  = disk.free  / (1024 ** 3)
        total = disk.total / (1024 ** 3)
        return f"Disk: {free:.0f} GB free of {total:.0f} GB ({disk.percent}% used)."
    except Exception as e:
        return f"Couldn't read disk: {e}"


def _battery() -> str | None:
    """Returns battery info only if a battery is present."""
    try:
        import psutil
        batt = psutil.sensors_battery()
        if batt is None:
            return None  # Desktop — no battery
        status = "charging" if batt.power_plugged else "discharging"
        return f"Battery at {int(batt.percent)}%, {status}."
    except Exception:
        return None


def _uptime() -> str:
    try:
        import psutil, time
        boot   = psutil.boot_time()
        uptime = int(time.time() - boot)
        h, r   = divmod(uptime, 3600)
        m, _   = divmod(r, 60)
        return f"Uptime: {h}h {m}m."
    except Exception:
        return ""


def _full_summary() -> str:
    parts = [_cpu(), _ram(), _disk(), _uptime()]
    batt  = _battery()
    if batt:
        parts.append(batt)
    return " ".join(parts)


SPECIFIC_KEYWORDS = {
    "cpu":      _cpu,
    "ram":      _ram,
    "memory":   _ram,
    "disk":     _disk,
    "storage":  _disk,
    "uptime":   _uptime,
    "battery":  _battery,
}


def run(query: str) -> str:
    try:
        import psutil  # noqa
    except ImportError:
        speak("System info requires psutil. Run pip install psutil.")
        return "Not installed: psutil"

    q = query.lower()

    # Specific request
    for keyword, fn in SPECIFIC_KEYWORDS.items():
        if keyword in q:
            if keyword == "battery":
                result = _battery()
                if result is None:
                    response = "No battery detected. You're on a desktop."
                else:
                    response = result
            else:
                response = fn()
            speak(response)
            return response

    # General — full summary
    summary = _full_summary()
    speak(summary)
    return summary