# run from JARVIS/ root: python test_speak.py
import sys
sys.path.insert(0, ".")
from bot.speaker import speak
speak("Testing. One, two, three.")