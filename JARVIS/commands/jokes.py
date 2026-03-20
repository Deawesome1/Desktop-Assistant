"""
commands/jokes.py — Tell a random joke.
Triggers: "tell me a joke", "say a joke", "joke"
Fetches from icanhazdadjoke.com (requires internet) with offline fallback.
"""
import urllib.request
import json
import random
from bot.speaker import speak

FALLBACK_JOKES = [
    "Why don't scientists trust atoms? Because they make up everything.",
    "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I asked the IT guy, how do you make a computer fast? He said, stop feeding it.",
    "Why did the scarecrow win an award? Because he was outstanding in his field.",
]

def run(query: str) -> str:
    try:
        req = urllib.request.Request(
            "https://icanhazdadjoke.com/",
            headers={"Accept": "application/json", "User-Agent": "JARVIS/1.0"}
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            joke = json.loads(resp.read())["joke"]
    except Exception:
        joke = random.choice(FALLBACK_JOKES)

    speak(joke)
    return joke