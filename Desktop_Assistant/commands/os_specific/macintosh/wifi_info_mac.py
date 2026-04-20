"""
wifi_info_mac.py — JARVIS Command (macOS)
Report WiFi SSID, signal strength, and link speed using airport.
"""

import subprocess
import re
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME = "wifi_info"
COMMAND_ALIASES = ["wifi", "wi-fi", "wifi info", "network info", "internet info"]
COMMAND_DESCRIPTION = "Reports WiFi SSID, signal strength, and speed on macOS."
COMMAND_OS_SUPPORT = ["macintosh"]
COMMAND_CATEGORY = "network"
COMMAND_REQUIRES_INTERNET = False
COMMAND_REQUIRES_ADMIN = False


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
    return os_key == "macintosh"


# ---------------------------------------------------------------------------
# Helper: parse airport output
# ---------------------------------------------------------------------------

def _get_wifi_info() -> Optional[Dict[str, Any]]:
    try:
        result = subprocess.run(
            [
                "/System/Library/PrivateFrameworks/Apple80211.framework/"
                "Versions/Current/Resources/airport",
                "-I"
            ],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout.lower()

        if "ssid" not in output:
            return None

        ssid = re.search(r"ssid:\s*(.+)", output)
        rssi = re.search(r"agrctlrssi:\s*(-?\d+)", output)
        txrate = re.search(r"lasttxrate:\s*(\d+)", output)

        # Convert RSSI to approximate signal %
        signal = None
        if rssi:
            rssi_val = int(rssi.group(1))
            signal = max(0, min(100, 2 * (rssi_val + 100)))

        return {
            "ssid": ssid.group(1).strip() if ssid else None,
            "signal": signal,
            "speed": int(txrate.group(1)) if txrate else None,
        }

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public run() entrypoint
# ---------------------------------------------------------------------------

def run(
    brain: Brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
):
    info = _get_wifi_info()

    if not info or not info.get("ssid"):
        brain.event("user_confused")
        return {
            "success": False,
            "message": "You don't appear to be connected to a WiFi network.",
            "data": {"connected": False},
        }

    ssid = info["ssid"]
    signal = f"{info['signal']}% signal" if info["signal"] else ""
    speed = f" at {info['speed']} Mbps" if info["speed"] else ""

    parts = ", ".join(p for p in [ssid, signal] if p)
    msg = f"Connected to {parts}{speed}."

    brain.event("task_success")
    brain.remember("wifi_queries", ssid)

    return {
        "success": True,
        "message": msg,
        "data": info,
    }
