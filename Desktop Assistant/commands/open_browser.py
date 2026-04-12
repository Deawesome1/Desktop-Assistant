"""
commands/open_browser.py — Open browser, optionally searching for something.
Triggers: "open browser", "search for X", "google X", "look up X"
"""
import webbrowser
from urllib.parse import quote
from bot.speaker import speak

def run(query: str) -> str:
    q = query.lower()

    # Extract search term if present
    for prefix in ["search for", "google", "look up", "search"]:
        if prefix in q:
            term = q.split(prefix, 1)[-1].strip()
            if term:
                url = f"https://www.google.com/search?q={quote(term)}"
                webbrowser.open(url)
                response = f"Searching for {term}."
                speak(response)
                return response

    # Bare "open browser" — just open homepage
    webbrowser.open("https://www.google.com")
    response = "Opening your browser."
    speak(response)
    return response