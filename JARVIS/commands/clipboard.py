"""
commands/clipboard.py — Cross-platform clipboard read/clear.
Windows/Mac: tkinter. Linux: xclip/xsel.
"""
from bot.speaker import speak
from JARVIS.platform_utils import get_clipboard, clear_clipboard


def run(query: str) -> str:
    q = query.lower()

    if "clear" in q:
        clear_clipboard()
        speak("Clipboard cleared.")
        return "Clipboard cleared."

    content = get_clipboard()
    if not content:
        speak("Your clipboard is empty.")
        return "Clipboard was empty."

    preview = content.strip()[:200]
    speak(f"Your clipboard contains: {preview}")
    return f"Clipboard read: {preview}"