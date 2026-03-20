"""
commands/media_control.py — Control media playback via keyboard media keys.
Triggers: "pause", "play", "next song", "previous song", "skip"
Requires: pyautogui  (pip install pyautogui)
"""
from bot.speaker import speak

KEY_MAP = {
    "pause":    "playpause",
    "play":     "playpause",
    "stop":     "playpause",
    "next":     "nexttrack",
    "skip":     "nexttrack",
    "previous": "prevtrack",
    "back":     "prevtrack",
    "last song":"prevtrack",
    "next song":"nexttrack",
}

def run(query: str) -> str:
    try:
        import pyautogui
        q = query.lower()

        key = None
        label = None
        for trigger, media_key in KEY_MAP.items():
            if trigger in q:
                key = media_key
                label = trigger
                break

        if not key:
            speak("I didn't catch which media control you wanted.")
            return "No media key matched."

        pyautogui.press(key)
        speak(f"Media: {label}.")
        return f"Pressed media key: {key}"

    except ImportError:
        speak("Media control requires pyautogui. Run pip install pyautogui.")
        return "pyautogui not installed."
    except Exception as e:
        speak("I couldn't control media playback.")
        return f"Media control error: {e}"