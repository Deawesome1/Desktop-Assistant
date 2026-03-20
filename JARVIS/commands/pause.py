"""
commands/pause.py — Buffer/pause command.
Stops JARVIS from speaking mid-sentence and keeps the session open,
waiting for a new command without requiring the wake word again.

Triggers: "hold on", "wait", "pause jarvis", "stop talking", "quiet"

Returns a special sentinel string "__STAY_AWAKE__" which main.py checks
to skip returning to idle and instead wait for another command directly.
"""
import pyttsx3
from bot.speaker import speak

def run(query: str) -> str:
    # Interrupt any ongoing speech by reinitializing the engine
    try:
        engine = pyttsx3.init()
        engine.stop()
    except Exception:
        pass

    speak("Ready.")
    return "__STAY_AWAKE__"