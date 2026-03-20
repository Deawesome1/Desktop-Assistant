"""
commands/screenshot.py — Cross-platform screenshot.
Windows/Mac: Pillow ImageGrab. Linux: scrot fallback.
"""
from datetime import datetime
import os
from bot.speaker import speak
from JARVIS.platform_utils import get_desktop, take_screenshot


def run(query: str) -> str:
    desktop  = get_desktop()
    filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(desktop, filename)

    if take_screenshot(filepath):
        response = f"Screenshot saved to Desktop as {filename}."
        speak(response)
        return response
    else:
        speak("I couldn't take a screenshot. Make sure Pillow is installed.")
        return "Failed: screenshot failed"