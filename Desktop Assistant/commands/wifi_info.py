"""
commands/wifi_info.py — Cross-platform WiFi info.
Windows: netsh. Mac: airport. Linux: iwgetid.
"""
from bot.speaker import speak
from JARVIS.platform_utils import get_wifi_info


def run(query: str) -> str:
    info = get_wifi_info()

    if not info:
        speak("You don't appear to be connected to a WiFi network.")
        return "Not connected to WiFi."

    ssid   = info["ssid"]
    signal = f"{info['signal']} percent signal" if info["signal"] else ""
    speed  = f" at {info['speed']:.0f} Mbps" if info["speed"] else ""
    parts  = filter(None, [ssid, signal])
    response = f"Connected to {', '.join(parts)}{speed}."
    speak(response)
    return response