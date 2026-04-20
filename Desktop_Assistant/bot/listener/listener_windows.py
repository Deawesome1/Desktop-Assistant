"""
listener_windows.py — Windows listener using SpeechRecognition + PyAudio.
"""

import logging
import speech_recognition as sr

logger = logging.getLogger("jarvis.listener.windows")

def listen(brain=None) -> str:
    """
    Windows listener:
        - Uses SpeechRecognition with PyAudio backend
        - Falls back to console input if audio fails
    """

    try:
        recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            print("You: ", end="", flush=True)
            audio = recognizer.listen(source)

        text = recognizer.recognize_sphinx(audio)
        logger.info(f"LISTEN(win): {text}")
        return text

    except Exception as e:
        logger.warning(f"Windows audio failed, falling back to console input: {e}")
        text = input("You: ")
        logger.info(f"LISTEN(win-fallback): {text}")
        return text
