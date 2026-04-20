"""
runtime.py — Main runtime loop for JARVIS (Omega)

This module ties together:
    - Brain (cognition, memory, mood, personality)
    - CommandHub (routing, logging, safety)
    - bot.listener (OS-aware input)
    - bot.speaker (OS-aware output)
    - BotContext (runtime state)

This is the heart of the assistant.
"""

import logging
from brain import get_brain
from commands.core.command_hub import CommandHub
from bot.listener import listener
from bot.speaker import speaker
from bot.context import BotContext


logger = logging.getLogger("jarvis.runtime")


def run(debug: bool = False, dry_run: bool = False):
    """
    Start the JARVIS runtime loop.
    """

    # Initialize core systems
    brain = get_brain()
    hub = CommandHub(brain, debug=debug, dry_run=dry_run)
    ctx = BotContext()

    speak("JARVIS online.", brain=brain)
    logger.info("Runtime started.")

    # Main loop
    while ctx.running:
        try:
            user_text = listen(brain)

            if not user_text.strip():
                continue

            # Graceful shutdown commands
            if user_text.lower() in ("exit", "quit", "shutdown", "bye"):
                speak("Shutting down.", brain=brain)
                logger.info("Shutdown requested by user.")
                ctx.running = False
                break

            # Execute through CommandHub
            result = hub.execute(user_text)

            # Speak result
            speak(result["message"], brain=brain)

            # Update runtime context
            ctx.update(user_text, result["message"])

        except KeyboardInterrupt:
            speak("Interrupted. Shutting down.", brain=brain)
            logger.info("KeyboardInterrupt — shutting down.")
            break

        except Exception as e:
            logger.exception(f"Runtime error: {e}")
            speak("Something went wrong, but I'm still here.", brain=brain)

    logger.info("Runtime stopped.")
