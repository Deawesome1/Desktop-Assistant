# Desktop_Assistant/listener/listener_mac.py
import logging
import speech_recognition as sr

from Desktop_Assistant.bot.speaker import speak_async
from Desktop_Assistant import imports as I

logger = logging.getLogger("jarvis.listener.mac")


def listen(brain=None) -> str:
    """
    macOS listener:
      - Calibrates ambient noise
      - Attempts Sphinx offline recognition; falls back to console input
      - Uses non-blocking TTS for feedback
    """
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.6
    recognizer.energy_threshold = 300

    try:
        mic = sr.Microphone()
    except Exception as e:
        logger.warning("No microphone available: %s", e)
        return _fallback_input(brain, "mac")

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
            # Prefer local Sphinx on mac; if not available, try Google
            try:
                text = recognizer.recognize_sphinx(audio)
            except Exception:
                text = recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            logger.debug("STT: didn't catch that")
            return ""
        except sr.RequestError as e:
            logger.warning("STT request error: %s", e)
            return ""

        logger.info("LISTEN(mac): %s", text)
        try:
            speak_async(f"You said: {text}", brain=brain)
        except Exception:
            logger.exception("Failed to speak recognized text (async)")
        return text

    except Exception as e:
        logger.warning("macOS audio failed, falling back to console input: %s", e)
        return _fallback_input(brain, "mac")


def _fallback_input(brain, platform_label="mac"):
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
