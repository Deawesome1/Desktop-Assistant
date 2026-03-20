"""
commands/clipboard_history.py — Track and recall clipboard history.
Stores last 10 clipboard items in memory during the session.
Triggers: "clipboard history", "last copied", "recall clipboard", "paste number X"
"""
import tkinter as tk
from bot.speaker import speak

_history: list[str] = []
MAX_HISTORY = 10


def _get_clipboard() -> str | None:
    try:
        root = tk.Tk()
        root.withdraw()
        content = root.clipboard_get()
        root.destroy()
        return content.strip() if content.strip() else None
    except Exception:
        return None


def record():
    """Call periodically or before each command to capture clipboard changes."""
    content = _get_clipboard()
    if content and (not _history or _history[-1] != content):
        _history.append(content)
        if len(_history) > MAX_HISTORY:
            _history.pop(0)


def run(query: str) -> str:
    q = query.lower()
    record()

    # Recall specific item: "paste number 2" or "clipboard 3"
    import re
    m = re.search(r"(\d+)", q)
    if m and any(w in q for w in ["number", "item", "paste", "#"]):
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(_history):
            item = _history[idx]
            preview = item[:100]
            speak(f"Clipboard item {idx + 1}: {preview}")
            return f"Clipboard item {idx + 1}: {preview}"
        else:
            speak(f"I only have {len(_history)} items in clipboard history.")
            return f"Failed: index {idx + 1} out of range"

    # List history
    if not _history:
        speak("Clipboard history is empty.")
        return "Empty clipboard history."

    speak(f"I have {len(_history)} clipboard items.")
    for i, item in enumerate(_history[-5:], 1):
        preview = item[:60].replace("\n", " ")
        speak(f"{i}: {preview}")

    return f"Listed {len(_history)} clipboard items."