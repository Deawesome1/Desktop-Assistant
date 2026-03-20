"""
commands/youtube.py — Search YouTube or open a specific video in the browser.
Triggers: "youtube", "search youtube for", "play on youtube", "open youtube"
"""
import webbrowser
import urllib.parse
from bot.speaker import speak


def run(query: str) -> str:
    q = query.lower()

    for prefix in ["search youtube for", "play on youtube", "youtube search",
                   "search on youtube", "open youtube for", "youtube"]:
        if prefix in q:
            search_term = q.split(prefix, 1)[-1].strip()
            break
    else:
        search_term = ""

    if not search_term:
        webbrowser.open("https://www.youtube.com")
        speak("Opening YouTube.")
        return "Opened YouTube."

    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_term)}"
    webbrowser.open(url)
    response = f"Searching YouTube for {search_term}."
    speak(response)
    return response