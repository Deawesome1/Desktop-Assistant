import sys
import traceback

print("Python executable:", sys.executable)

try:
    import speech_recognition as sr
    print("✓ speech_recognition imported")
except Exception as e:
    print("❌ Failed to import speech_recognition:", e)
    traceback.print_exc()

try:
    import pyaudio
    print("✓ PyAudio imported")
except Exception as e:
    print("❌ Failed to import PyAudio:", e)
    traceback.print_exc()

print("\n--- Testing microphone ---\n")

try:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("✓ Microphone opened successfully")
        print("Say something...")
        audio = r.listen(source, timeout=5)
        print("✓ Audio captured")
except Exception as e:
    print("❌ Microphone test failed:", e)
    traceback.print_exc()
