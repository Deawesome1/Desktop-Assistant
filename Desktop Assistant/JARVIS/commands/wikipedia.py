"""
commands/wikipedia.py — Get a quick Wikipedia summary.
Triggers: "wikipedia X", "wiki X", "who is X", "what is X"
Requires: wikipedia-api  (pip install wikipedia-api)
"""
import re
from bot.speaker import speak

def run(query: str) -> str:
    q = query.strip()

    # Extract the search subject
    subject = q
    for prefix in ["wikipedia", "wiki", "who is", "who was", "what is", "what are", "tell me about"]:
        if prefix in q.lower():
            subject = q.lower().split(prefix, 1)[-1].strip(" ?")
            break

    if not subject:
        speak("What would you like me to look up?")
        return "No subject given."

    try:
        import wikipediaapi
        wiki = wikipediaapi.Wikipedia(
            language="en",
            user_agent="JARVIS/1.0"
        )
        page = wiki.page(subject)
        if not page.exists():
            speak(f"I couldn't find a Wikipedia page for {subject}.")
            return f"No Wikipedia page: {subject}"

        # Read first ~500 chars — enough for a spoken summary
        summary = page.summary[:500].strip()
        # Trim to last complete sentence
        last_period = summary.rfind(".")
        if last_period > 100:
            summary = summary[:last_period + 1]

        speak(summary)
        return summary

    except ImportError:
        speak("Wikipedia lookup requires wikipedia-api. Run pip install wikipedia-api.")
        return "wikipedia-api not installed."
    except Exception as e:
        speak("I had trouble fetching that from Wikipedia.")
        return f"Wikipedia error: {e}"