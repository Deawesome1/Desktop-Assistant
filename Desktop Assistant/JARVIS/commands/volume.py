"""
commands/volume.py — Cross-platform volume control.
Windows: pycaw (precise) with PowerShell fallback.
Mac:     osascript.
Linux:   pactl (PulseAudio/PipeWire) with amixer fallback.
"""
import re
from bot.speaker import speak
from JARVIS.platform_utils import get_volume, set_volume, mute


def run(query: str) -> str:
    q = query.lower()

    if "unmute" in q:
        mute(False)
        speak("Unmuted.")
        return "Unmuted."

    if "mute" in q:
        mute(True)
        speak("Muted.")
        return "Muted."

    match = re.search(r"(\d+)", q)
    if match and any(p in q for p in ["set volume", "volume to", "set it to"]):
        level = max(0, min(100, int(match.group(1))))
        set_volume(level)
        response = f"Volume set to {level} percent."
        speak(response)
        return response

    current = get_volume()

    if any(w in q for w in ["up", "increase", "louder", "raise"]):
        new = min(100, (current or 50) + 10)
        set_volume(new)
        response = f"Volume up to {new} percent."
        speak(response)
        return response

    if any(w in q for w in ["down", "decrease", "quieter", "lower"]):
        new = max(0, (current or 50) - 10)
        set_volume(new)
        response = f"Volume down to {new} percent."
        speak(response)
        return response

    if current is not None:
        response = f"Volume is at {current} percent."
    else:
        response = "I couldn't read the volume level."
    speak(response)
    return response