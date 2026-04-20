# test_speaker_queue.py — run from JARVIS/ root
import sys, os
sys.path.insert(0, ".")

# Simulate exactly what happens during a command
from bot.speaker import speak, get_response

print("Test 1: wake acknowledged")
speak(get_response("wake_acknowledged"))
print("Test 1 done")

print("Test 2: waiting for command")
speak(get_response("waiting_for_command"))
print("Test 2 done")

print("Test 3: command response")
speak("The time is 12 05 AM.")
print("Test 3 done")