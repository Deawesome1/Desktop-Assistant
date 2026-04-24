# speaker_windows.py
import logging

logger = logging.getLogger("jarvis.speaker.windows")

try:
    import win32com.client
    _speaker = win32com.client.Dispatch("SAPI.SpVoice")
except Exception as e:
    _speaker = None
    logger.warning("Windows TTS initialization failed: %s", e)

# SAPI flag for async speak (1 == SVSFlagsAsync)
_SAPI_ASYNC_FLAG = 1

def speak(text: str, *, brain=None, block: bool = True) -> None:
    print(f"JARVIS: {text}")
    logger.info("SPEAK(win): %s", text)

    if _speaker is None:
        logger.debug("No SAPI speaker available")
        return

    try:
        if block:
            # synchronous speak
            _speaker.Speak(text)
        else:
            # async speak using SAPI flag
            try:
                _speaker.Speak(text, _SAPI_ASYNC_FLAG)
            except Exception:
                # fallback to non-flagged call in a thread if SAPI flags not supported
                import threading
                threading.Thread(target=lambda: _speaker.Speak(text), daemon=True).start()
    except Exception as e:
        logger.warning("Windows TTS failed: %s", e)
