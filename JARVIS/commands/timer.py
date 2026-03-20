"""
commands/timer.py — Set a countdown timer.
Triggers: "set a timer for X minutes", "timer for X seconds", "remind me in X minutes"
Runs the countdown in a background thread so JARVIS stays responsive.
"""
import re
import threading
import time
from bot.speaker import speak

def run(query: str) -> str:
    q = query.lower()

    seconds = 0
    patterns = [
        (r"(\d+)\s*hour",   3600),
        (r"(\d+)\s*minute", 60),
        (r"(\d+)\s*second", 1),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, q)
        if match:
            seconds += int(match.group(1)) * multiplier

    if seconds <= 0:
        speak("I didn't catch how long. Try saying: set a timer for 5 minutes.")
        return "No duration parsed."

    parts = []
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h: parts.append(f"{h} hour{'s' if h > 1 else ''}")
    if m: parts.append(f"{m} minute{'s' if m > 1 else ''}")
    if s: parts.append(f"{s} second{'s' if s > 1 else ''}")
    label = " and ".join(parts)

    speak(f"Timer set for {label}.")

    def _countdown():
        time.sleep(seconds)
        speak(f"Your {label} timer is done.")

    threading.Thread(target=_countdown, daemon=True).start()
    return f"Timer started: {label}."