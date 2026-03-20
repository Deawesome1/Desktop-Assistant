"""
commands/exit_command.py — Gracefully exit JARVIS or acknowledge a cancel.
Triggers: "goodbye", "exit", "quit jarvis", "bye"

Note: "cancel" and "never mind" are handled by is_cancel() in listener.py
and never reach the command hub. This command handles explicit exit intent.
"""
import os
import sys
from bot.speaker import speak


def run(query: str) -> str:
    q = query.lower()

    # Soft cancel acknowledgement (shouldn't normally reach here, but just in case)
    if any(w in q for w in ["cancel", "never mind", "nevermind", "stop"]):
        speak("Okay.")
        return "Cancel acknowledged."

    # Hard exit — shut JARVIS down cleanly
    speak("Goodbye.")
    # Small delay so TTS finishes before process exits
    import time
    time.sleep(1.5)
    os._exit(0)