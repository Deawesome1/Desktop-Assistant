# Desktop_Assistant/bot/speaker.py
"""
TTS queue worker (Windows SAPI safe) + cross-platform wrapper.
- speak(text, block=True) enqueues and optionally waits.
- speak_async(text) enqueues and returns immediately.
"""

import logging
import threading
import queue
import time
from typing import Optional

logger = logging.getLogger("jarvis.speaker")

# Worker queue and control
_tts_queue: "queue.Queue[tuple[str, threading.Event|None]]" = queue.Queue()
_worker_thread: Optional[threading.Thread] = None
_worker_ready = threading.Event()
_shutdown = threading.Event()

# Platform backend loader (only used inside worker)
def _worker():
    """
    Worker thread: initialize COM and SAPI inside this thread (Windows),
    then process queue items synchronously.
    """
    try:
        # Import here so it's in the worker thread
        import pythoncom
        import win32com.client
    except Exception as e:
        logger.warning("TTS worker: platform TTS backend not available: %s", e)
        # Drain queue and print instead
        while not _shutdown.is_set():
            try:
                text, ev = _tts_queue.get(timeout=0.2)
            except Exception:
                if _shutdown.is_set():
                    break
                continue
            try:
                print(f"JARVIS: {text}")
            finally:
                if ev:
                    ev.set()
        return

    # Initialize COM for this thread
    pythoncom.CoInitialize()
    try:
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
    except Exception as e:
        logger.exception("TTS worker: failed to create SAPI.SpVoice: %s", e)
        pythoncom.CoUninitialize()
        # fallback: drain queue printing
        while not _shutdown.is_set():
            try:
                text, ev = _tts_queue.get(timeout=0.2)
            except Exception:
                if _shutdown.is_set():
                    break
                continue
            try:
                print(f"JARVIS: {text}")
            finally:
                if ev:
                    ev.set()
        return

    # Worker ready
    _worker_ready.set()
    logger.debug("TTS worker started (SAPI ready)")

    try:
        while not _shutdown.is_set():
            try:
                text, ev = _tts_queue.get(timeout=0.2)
            except Exception:
                continue
            try:
                # Synchronous speak in worker thread
                speaker.Speak(text)
            except Exception:
                logger.exception("TTS worker: SAPI.Speak failed for text: %s", text)
            finally:
                if ev:
                    ev.set()
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
        logger.debug("TTS worker exiting")


def _ensure_worker():
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _shutdown.clear()
    _worker_ready.clear()
    _worker_thread = threading.Thread(target=_worker, daemon=True)
    _worker_thread.start()
    # Wait briefly for worker to initialize (non-blocking caller can still proceed)
    _worker_ready.wait(timeout=1.0)


def speak(text: str, *, brain=None, block: bool = True) -> None:
    """
    Enqueue text for speaking. If block=True, wait until the worker finishes speaking it.
    """
    if not text:
        return
    _ensure_worker()
    ev = threading.Event() if block else None
    _tts_queue.put((text, ev))
    if block and ev:
        # Wait with a timeout to avoid indefinite hangs
        ev.wait(timeout=30.0)


def speak_async(text: str, *, brain=None) -> None:
    """Enqueue text and return immediately."""
    speak(text, brain=brain, block=False)


def shutdown():
    """Signal worker to exit (call at process shutdown if desired)."""
    _shutdown.set()
    if _worker_thread:
        _worker_thread.join(timeout=1.0)
