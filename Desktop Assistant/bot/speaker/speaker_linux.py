"""
speaker_linux.py — Linux TTS using 'espeak' (if installed).
"""

import os
import logging

logger = logging.getLogger("jarvis.speaker.linux")

def speak(text: str, *, brain=None) -> None:
    """
    Speak text on Linux using 'espeak' if available.
    Always prints to console as well.
    """
    print(f"JARVIS: {text}")
    logger.info(f"SPEAK(linux): {text}")

    try:
        os.system(f'espeak "{text}"')
    except Exception as e:
        logger.warning(f"Linux TTS failed: {e}")
