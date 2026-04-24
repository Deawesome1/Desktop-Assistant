# Desktop_Assistant/listener/listener_windows.py
import logging
import speech_recognition as sr

from Desktop_Assistant.bot.speaker import speak_async
from Desktop_Assistant import imports as I

logger = logging.getLogger("jarvis.listener.windows")


def listen(brain=None) -> str:
    """
    Windows listener:
      - Calibrates ambient noise
      - Uses Google STT (or configured recognizer)
      - Falls back to console input if audio fails
      - Uses non-blocking TTS for responses
    """
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.6
    # Starting energy threshold; tune if needed
    recognizer.energy_threshold = 300

    try:
        mic = sr.Microphone()
    except Exception as e:
        logger.warning("No microphone available: %s", e)
        return _fallback_input(brain, "windows")

    # Calibrate ambient noise once per listen call (short)
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1.0)
    except Exception:
        logger.debug("Ambient noise calibration failed (continuing)")

    try:
        with mic as source:
            print("You: ", end="", flush=True)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=6)

        try:
            text = recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            logger.debug("STT: didn't catch that")
            return ""
        except sr.RequestError as e:
            logger.warning("STT request error: %s", e)
            return ""

        logger.info("LISTEN(win): %s", text)
        # Non-blocking feedback
        try:
            speak_async(f"You said: {text}", brain=brain)
        except Exception:
            logger.exception("Failed to speak recognized text (async)")

        return text

    except Exception as e:
        logger.warning("Windows audio failed, falling back to console input: %s", e)
        return _fallback_input(brain, "windows")


def _fallback_input(brain, platform_label="windows"):
    try:
        text = input("You: ")
    except Exception:
        text = ""
    logger.info("LISTEN(%s-fallback): %s", platform_label, text)
    try:
        speak_async(f"You said: {text}", brain=brain)
    except Exception:
        logger.exception("Failed to speak fallback text")
    return text
