"""
commands/time.py — Tell the current time.
"""
from datetime import datetime
from bot.speaker import speak

def run(query: str) -> str:
    time_str = datetime.now().strftime("%I:%M %p").lstrip("0")
    response = f"The time is {time_str}."
    speak(response)
    return response