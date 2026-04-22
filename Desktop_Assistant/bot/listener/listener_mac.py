"""
listener_mac.py — macOS listener using SpeechRecognition + AVFoundation fallback.
"""

import logging
import speech_recognition as sr

logger = logging.getLogger("jarvis.listener.mac")


def listen(brain=None) -> str:
    """
    macOS listener:
        - Attempts microphone input via SpeechRecognition
        - Falls back to console input if audio fails
    """

    try:
        recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            print("You: ", end="", flush=True)
            audio = recognizer.listen(source)

        # Offline Sphinx fallback (macOS-friendly)
        text = recognizer.recognize_sphinx(audio)
        logger.info(f"LISTEN(mac): {text}")
        return text

    except Exception as e:
        logger.warning(f"macOS audio failed, falling back to console input: {e}")
        text = input("You: ")
        logger.info(f"LISTEN(mac-fallback): {text}")
        return text
