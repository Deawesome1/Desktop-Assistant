# runtime/voice_runtime.py

import sys
import traceback
import time
from Desktop_Assistant import imports as I

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


def init_tts():
    if pyttsx3 is None:
        print("[Voice] TTS unavailable.")
        return None
    try:
        return pyttsx3.init()
    except:
        return None


def speak(engine, text):
    if engine:
        engine.say(text)
        engine.runAndWait()
    else:
        print(f"JARVIS (voice-disabled): {text}")


def init_mic():
    if sr is None:
        print("[Voice] speech_recognition unavailable.")
        return None, None
    recognizer = sr.Recognizer()
    try:
        mic = sr.Microphone()
    except:
        mic = None
    return recognizer, mic


def voice_runtime():
    print("\n[Voice Mode] Initializing…")

    try:
        Brain = I.Brain()
        brain = Brain()
    except Exception as e:
        print("FATAL: Could not initialize Brain.")
        print(e)
        sys.exit(1)

    tts = init_tts()
    recognizer, mic = init_mic()

    if mic is None:
        print("[Voice] No microphone detected — fallback to REPL.")
        from .repl_runtime import repl_runtime
        return repl_runtime()

    speak(tts, "Voice mode online. Say 'exit' to shut me down.")

    while True:
        try:
            print("[Voice] Listening…")
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source)

            try:
                user_text = recognizer.recognize_google(audio)
                print(f"You (voice): {user_text}")
            except:
                print("[Voice] Didn't catch that.")
                continue

            if user_text.lower() in ("exit", "quit", "shutdown", "stop"):
                speak(tts, "Goodbye.")
                break

            result = brain.process(user_text)
            msg = result.get("message", "") if isinstance(result, dict) else str(result)

            print(f"JARVIS: {msg}")
            speak(tts, msg)

        except KeyboardInterrupt:
            speak(tts, "Interrupted. Say exit to shut me down.")
        except Exception as e:
            print("[Voice] Unexpected error.")
            print(traceback.format_exc())
