"""
commands/youtube.py — Search YouTube or open a specific video in the browser.
Triggers: "youtube", "search youtube for", "play on youtube", "open youtube"
"""
import re
import webbrowser
import urllib.parse
from bot.speaker import speak

# Ordered longest-first so "search youtube for" beats "youtube"
PREFIXES = [
    "search youtube for",
    "play on youtube",
    "youtube search for",
    "youtube search",
    "search on youtube for",
    "search on youtube",
    "open youtube for",
    "look up on youtube",
    "look up youtube",
    "on youtube search",
    "on youtube look up",
    "on youtube",
]


def run(query: str) -> str:
    q = query.lower().strip()
    # Normalize "youtubes" -> "youtube" so STT errors don't break matching
    q = re.sub(r'\byoutubes\b', 'youtube', q)

    search_term = ""

    # "look up X on youtube" — check this FIRST before prefix stripping
    m = re.search(r'look up (.+?) on youtube', q)
    if m:
        search_term = m.group(1).strip()

    # Try explicit prefix matches (longest first)
    if not search_term:
        for prefix in PREFIXES:
            if prefix in q:
                search_term = q.split(prefix, 1)[-1].strip()
                break

    # Fallback: extract term after "youtube" as a whole word
    if not search_term:
        m = re.search(r'\byoutube\b\s*(.*)', q)
        if m:
            search_term = m.group(1).strip()

    if not search_term:
        webbrowser.open("https://www.youtube.com")
        speak("Opening YouTube.")
        return "Opened YouTube."

    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_term)}"
    webbrowser.open(url)
    response = f"Searching YouTube for {search_term}."
    speak(response)
    return response