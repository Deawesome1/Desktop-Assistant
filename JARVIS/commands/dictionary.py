"""
commands/dictionary.py — Define a word using the Free Dictionary API.
Triggers: "define", "what does X mean", "definition of", "meaning of"
No API key required.
"""
import re
import json
import urllib.request
import urllib.parse
import urllib.error
from bot.speaker import speak


def run(query: str) -> str:
    q = query.lower().strip(" ?.,")
    # Strip trigger phrases in order of length (longest first) to avoid partial matches
    for prefix in sorted([
        "what is the meaning of", "what's the meaning of",
        "definition of", "meaning of",
        "what does", "define",
    ], key=len, reverse=True):
        if q.startswith(prefix):
            q = q[len(prefix):].strip(" ?.,")
            break
    # Strip trailing filler like "mean" or "means"
    q = re.sub(r"\s+means?$", "", q).strip(" ?.,")
    word = q.strip()

    if not word:
        speak("Which word would you like me to define?")
        return "Failed: no word given"

    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())

        entry    = data[0]
        meanings = entry.get("meanings", [])
        if not meanings:
            speak(f"I found {word} but couldn't get a definition.")
            return f"No definitions for {word}"

        part_of_speech = meanings[0].get("partOfSpeech", "")
        definition     = meanings[0]["definitions"][0].get("definition", "")
        example        = meanings[0]["definitions"][0].get("example", "")

        response = f"{word}: {part_of_speech}. {definition}"
        if example:
            response += f" For example: {example}"

        speak(response)
        return response

    except urllib.error.HTTPError:
        speak(f"I couldn't find a definition for {word}.")
        return f"Failed: no definition found for '{word}'"
    except Exception as e:
        speak("I couldn't reach the dictionary right now.")
        return f"Failed: {e}"