"""
speaker_mac.py — macOS TTS using 'say' command.
"""

import os
import logging

logger = logging.getLogger("jarvis.speaker.mac")

def speak(text: str, *, brain=None) -> None:
    print(f"JARVIS: {text}")
    logger.info(f"SPEAK(mac): {text}")

    try:
        os.system(f'say "{text}"')
    except Exception as e:
        logger.warning(f"macOS TTS failed: {e}")
