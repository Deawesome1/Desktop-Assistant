"""test/test_listener.py — Test microphone and wake word detection."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from bot.listener import listen_once, contains_wake_word, is_cancel

print("Mic list:")
try:
    import speech_recognition as sr
    print(sr.Microphone.list_microphone_names())
except Exception as e:
    print(f"  Error: {e}")

print("\nSay something:")
result = listen_once(prompt="Listening...", timeout=8)
print(f"Heard: '{result}'")
print(f"Contains wake word: {contains_wake_word(result or '')}")
print(f"Is cancel: {is_cancel(result or '')}")