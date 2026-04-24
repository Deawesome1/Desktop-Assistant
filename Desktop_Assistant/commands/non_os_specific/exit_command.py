# Desktop_Assistant/commands/non_os_specific/exit_command.py
import os
import time
import logging
from typing import Any, Dict, List, Optional
from Desktop_Assistant import imports as I

logger = logging.getLogger("jarvis.commands.exit")

COMMAND_NAME = "exit"
COMMAND_ALIASES = ["quit", "goodbye", "bye", "exit jarvis", "quit jarvis"]

def get_metadata() -> Dict[str, Any]:
    return {"name": COMMAND_NAME, "aliases": COMMAND_ALIASES, "category": "system"}

def run(brain, user_text: str, args: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Soft cancel handling omitted for brevity; keep your existing logic if needed.

    logger.info("Exit command invoked; preparing audible shutdown.")
    # Ensure brain analytics
    try:
        brain.event("task_success")
        brain.remember("exit_actions", "hard_exit")
    except Exception:
        logger.debug("Failed to record exit analytics", exc_info=True)

    # Import speak and shutdown helpers (best-effort)
    try:
        from Desktop_Assistant.bot.speaker import speak, shutdown as tts_shutdown
    except Exception:
        try:
            from Desktop_Assistant.bot import speak  # fallback
            tts_shutdown = None
        except Exception:
            # Last resort: print fallback
            speak = lambda text, **kw: print(f"JARVIS: {text}")
            tts_shutdown = None

    goodbye = "Goodbye. Talk soon."

    # Instrumentation: log before and after speak so we can see what happened
    logger.info("Speaking goodbye now (blocking).")
    try:
        speak(goodbye, block=True)
        logger.info("speak() returned successfully.")
    except Exception:
        logger.exception("speak() raised an exception during exit.")

    # Small grace to let audio hardware flush
    try:
        time.sleep(0.25)
    except Exception:
        pass

    # Attempt to shutdown TTS worker if available
    try:
        if callable(tts_shutdown):
            logger.info("Shutting down TTS worker.")
            tts_shutdown()
    except Exception:
        logger.exception("TTS shutdown failed.")

    # Force exit to avoid host interceptors preventing termination
    logger.info("Exiting process now.")
    os._exit(0)

    # unreachable
    return {"success": True, "message": "Exiting", "data": {"action": "exit"}}
