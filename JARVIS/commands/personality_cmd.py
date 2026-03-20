"""
commands/personality_cmd.py — Switch or reload the active personality.
Triggers: "change personality", "reload personality", "switch personality"
"""
import os
import json
from bot.speaker import speak
from bot.listener import listen_once

CONFIG_PATH      = os.path.join(os.path.dirname(__file__), "..", "config", "personality.json")
PERSONALITY_DIR  = os.path.join(os.path.dirname(__file__), "..", "bot", "personality")


def _list_personalities() -> list[str]:
    try:
        return [
            d for d in os.listdir(PERSONALITY_DIR)
            if os.path.isdir(os.path.join(PERSONALITY_DIR, d))
            and not d.startswith("_")
            and os.path.exists(os.path.join(PERSONALITY_DIR, d, "profile.json"))
        ]
    except Exception:
        return []


def run(query: str) -> str:
    q = query.lower()

    # Reload current personality
    if "reload" in q:
        try:
            from bot.personality.engine import reload
            reload()
            speak("Personality reloaded.")
            return "Personality reloaded."
        except Exception as e:
            speak("Couldn't reload personality.")
            return f"Failed: {e}"

    # List or switch
    personalities = _list_personalities()

    if len(personalities) == 1:
        speak(f"Only one personality available: {personalities[0]}. "
              f"Copy the personality folder to create a new one.")
        return f"Only one personality: {personalities[0]}"

    speak(f"Available personalities: {', '.join(personalities)}. Which would you like?")
    choice = listen_once(timeout=6)

    if not choice:
        speak("No change made.")
        return "No change."

    choice_lower = choice.lower().strip()
    match = next((p for p in personalities if p.lower() == choice_lower), None)

    if not match:
        speak(f"I couldn't find a personality called {choice}.")
        return f"Failed: no personality '{choice}'"

    try:
        config = json.load(open(CONFIG_PATH))
        config["active"] = match
        json.dump(config, open(CONFIG_PATH, "w"), indent=2)
        from bot.personality.engine import reload
        reload()
        speak(f"Switched to {match}.")
        return f"Switched to {match}."
    except Exception as e:
        speak("Couldn't switch personality.")
        return f"Failed: {e}"