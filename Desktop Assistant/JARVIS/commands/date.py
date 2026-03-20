"""
commands/date.py — Tell today's date.
"""
from datetime import datetime
from bot.speaker import speak

def run(query: str) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")
    response = f"Today is {today}."
    speak(response)
    return response