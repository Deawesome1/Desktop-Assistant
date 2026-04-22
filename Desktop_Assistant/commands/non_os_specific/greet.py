"""
commands/greet.py — Greet the user.
"""

from Desktop_Assistant import imports as I


def run(query: str) -> str:
    response = "Hello. I'm JARVIS. What do you need?"
    I.speak(response)
    return response
