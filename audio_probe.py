# audio_probe.py

import sys
import traceback

print("[audio_probe] Python executable:", sys.executable)

try:
    import speech_recognition as sr
    print("[audio_probe] ✓ speech_recognition imported")
except Exception as e:
    print("[audio_probe] ❌ Failed to import speech_recognition:", e)
    traceback.print_exc()

try:
    import pyaudio
    print("[audio_probe] ✓ PyAudio imported")
except Exception as e:
    print("[audio_probe] ❌ Failed to import PyAudio:", e)
    traceback.print_exc()

print("\n[audio_probe] --- Testing microphone ---\n")

try:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("[audio_probe] ✓ Microphone opened successfully")
        print("[audio_probe] Say something...")
        audio = r.listen(source, timeout=5)
        print("[audio_probe] ✓ Audio captured")
except Exception as e:
    print("[audio_probe] ❌ Microphone test failed:", e)
    traceback.print_exc()
