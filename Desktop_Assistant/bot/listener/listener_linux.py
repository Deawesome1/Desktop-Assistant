"""
listener_linux.py — Linux listener using SpeechRecognition + PulseAudio backend.
"""

import logging
import speech_recognition as sr

logger = logging.getLogger("jarvis.listener.linux")

def listen(brain=None) -> str:
    """
    Linux listener:
        - Attempts microphone input
        - Falls back to console input
    """

    try:
        recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            print("You: ", end="", flush=True)
            audio = recognizer.listen(source)

        text = recognizer.recognize_sphinx(audio)
        logger.info(f"LISTEN(linux): {text}")
        return text

    except Exception as e:
        logger.warning(f"Linux audio failed, falling back to console input: {e}")
        text = input("You: ")
        logger.info(f"LISTEN(linux-fallback): {text}")
        return text
