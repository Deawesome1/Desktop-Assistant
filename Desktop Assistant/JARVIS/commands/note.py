"""
commands/note.py — Save spoken notes cross-platform.
Saves to Desktop/jarvis_notes.txt on any OS.
"""
import os
from datetime import datetime
from bot.speaker import speak
from bot.listener import listen_once
from JARVIS.platform_utils import get_desktop


def run(query: str) -> str:
    q = query.lower()

    content = q
    for prefix in ["take a note", "note this", "write this down", "remember this",
                   "make a note", "take note", "note"]:
        if prefix in q:
            content = q.split(prefix, 1)[-1].strip(" :,.")
            break

    if not content:
        speak("What would you like me to note?")
        heard = listen_once(timeout=8)
        if not heard:
            speak("I didn't catch anything. Note cancelled.")
            return "Failed: no content"
        content = heard.strip()

    notes_file = os.path.join(get_desktop(), "jarvis_notes.txt")
    timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry      = f"[{timestamp}] {content}\n"

    try:
        with open(notes_file, "a", encoding="utf-8") as f:
            f.write(entry)
        speak(f"Noted: {content}")
        return f"Note saved: {content}"
    except Exception as e:
        speak("I couldn't save the note.")
        return f"Failed: {e}"