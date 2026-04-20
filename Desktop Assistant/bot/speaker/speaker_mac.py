"""
speaker_mac.py — macOS TTS using 'say' command.
"""

import os
import logging

logger = logging.getLogger("jarvis.speaker.mac")

def speak(text: str, *, brain=None) -> None:
    """
    Speak text on macOS using the built-in 'say' command.
    Always prints to console as well.
    """
    print(f"JARVIS: {text}")
    logger.info(f"SPEAK(mac): {text}")

    try:
        os.system(f'say "{text}"')
    except Exception as e:
        logger.warning(f"macOS TTS failed: {e}")
