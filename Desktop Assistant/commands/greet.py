"""
commands/greet.py — Greet the user.
"""
from bot.speaker import speak

def run(query: str) -> str:
    response = "Hello. I'm JARVIS. What do you need?"
    speak(response)
    return response