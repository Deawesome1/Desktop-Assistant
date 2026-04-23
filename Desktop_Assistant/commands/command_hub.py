"""
command_hub.py — Central command router for JARVIS (Omega)

Responsibilities:
    - Receive user text
    - Ask Brain which command matches
    - Perform safety + intent checks
    - Execute commands (or dry-run)
    - Log everything (success, failure, timing, errors)
    - Update Brain state (events, last command, memory)
    - Provide hooks for advanced features (chaining, pipelines, etc.)
"""

import os
import time
import logging
from typing import Any, Dict, Optional

# Central import surface
from Desktop_Assistant import imports as I
Brain = I.Brain


# ----------------------------------------------------------------------
# Logging setup
# ----------------------------------------------------------------------

LOGGER_NAME = "jarvis.command_hub"


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.DEBUG)

    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [Hub] %(message)s",
        datefmt="%H:%M:%S",
    )
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler("logs/command_hub.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    return logger


logger = _setup_logger()


# ----------------------------------------------------------------------
# CommandHub Class
# ----------------------------------------------------------------------

class CommandHub:
    def __init__(self, brain: Brain, debug: bool = False, dry_run: bool = False):
        self.brain = brain
        self.debug = debug
        self.dry_run = dry_run

        if self.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("CommandHub initialized in DEBUG mode.")
        else:
            logger.debug("CommandHub initialized.")

    def handle(self, user_text: str):
        """
        Public wrapper so Brain.process() can call the hub cleanly.
        """
        return self.execute(user_text)


    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def execute(self, user_text: str) -> Dict[str, Any]:
        """
        Main entrypoint: route user_text to the correct command module.
        Returns a structured dict with success/message/data.
        """

        start_time = time.time()
        os_key = self.brain.get_current_os_key()
        intent = self.brain.detect_intent(user_text)

        if self.debug:
            logger.debug(f"Incoming text: {user_text!r}")
            logger.debug(f"Detected intent: {intent}")
            logger.debug(f"OS key: {os_key}")

        # 1. Safety check
        if not self.brain.is_action_allowed(user_text, intent):
            logger.warning(f"Blocked unsafe action. Intent={intent}, text={user_text!r}")
            self.brain.event("user_confused")
            return self._build_response(
                success=False,
                message="I can't help with that.",
                data={"blocked": True, "intent": intent, "reason": "safety_limits"},
                start_time=start_time,
                command_name=None,
                error_type="safety_block",
            )

        # 2. Command lookup
        module = self.brain.find_command(user_text)

        if not module:
            logger.info(f"No command matched for text: {user_text!r}")
            self.brain.event("user_confused")
            return self._build_response(
                success=False,
                message="I didn't understand that command.",
                data={"matched": False, "intent": intent},
                start_time=start_time,
                command_name=None,
                error_type="no_match",
            )

        meta = module.get_metadata()
        command_name = meta.get("name", "unknown")
        aliases = meta.get("aliases", [])
        category = meta.get("category", "unknown")

        if self.debug:
            logger.debug(f"Matched command: {command_name} (category={category}, aliases={aliases})")

        # 3. Update context
        self.brain.set_last_command(command_name)

        # 4. Dry-run mode
        if self.dry_run:
            logger.info(f"DRY RUN: would execute command '{command_name}'")
            return self._build_response(
                success=True,
                message=f"(Dry run) Would execute command '{command_name}'.",
                data={
                    "dry_run": True,
                    "command": command_name,
                    "intent": intent,
                    "category": category,
                },
                start_time=start_time,
                command_name=command_name,
            )

        # 5. Execute command
        try:
            if self.debug:
                logger.debug(f"Executing command '{command_name}'...")

            result = module.run(self.brain, user_text)

            if not isinstance(result, dict):
                result = {
                    "success": True,
                    "message": str(result),
                    "data": {},
                }

            success = bool(result.get("success", False))

            if success:
                self.brain.event("task_success")
                logger.info(f"Command '{command_name}' succeeded.")
            else:
                self.brain.event("user_confused")
                logger.warning(f"Command '{command_name}' reported failure.")

            return self._build_response(
                success=success,
                message=result.get("message", ""),
                data=result.get("data", {}),
                start_time=start_time,
                command_name=command_name,
                intent=intent,
                category=category,
            )

        except Exception as e:
            logger.exception(f"Command '{command_name}' crashed: {e}")
            self.brain.event("user_confused")

            return self._build_response(
                success=False,
                message=f"Command '{command_name}' failed.",
                data={"error": str(e)},
                start_time=start_time,
                command_name=command_name,
                intent=intent,
                category=category,
                error_type="exception",
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_response(
        self,
        success: bool,
        message: str,
        data: Optional[Dict[str, Any]],
        start_time: float,
        command_name: Optional[str],
        intent: Optional[str] = None,
        category: Optional[str] = None,
        error_type: Optional[str] = None,
    ) -> Dict[str, Any]:

        elapsed = time.time() - start_time

        # Logging summary
        if command_name:
            if success:
                logger.info(
                    f"Command '{command_name}' completed in {elapsed:.3f}s "
                    f"(intent={intent}, category={category})"
                )
            else:
                logger.warning(
                    f"Command '{command_name}' failed in {elapsed:.3f}s "
                    f"(intent={intent}, category={category}, error_type={error_type})"
                )
        else:
            if success:
                logger.info(f"Non-command response in {elapsed:.3f}s")
            else:
                logger.warning(
                    f"Non-command failure in {elapsed:.3f}s (error_type={error_type})"
                )

        # Analytics hook
        self._record_analytics(
            success=success,
            command_name=command_name,
            intent=intent,
            category=category,
            elapsed=elapsed,
            error_type=error_type,
        )

        return {
            "success": success,
            "message": message,
            "data": data or {},
            "meta": {
                "command": command_name,
                "intent": intent,
                "category": category,
                "elapsed": elapsed,
                "error_type": error_type,
            },
        }

    def _record_analytics(
        self,
        success: bool,
        command_name: Optional[str],
        intent: Optional[str],
        category: Optional[str],
        elapsed: float,
        error_type: Optional[str],
    ) -> None:

        if not command_name:
            return

        try:
            entry = {
                "command": command_name,
                "intent": intent,
                "category": category,
                "success": success,
                "elapsed": elapsed,
                "error_type": error_type,
                "timestamp": time.time(),
            }
            self.brain.remember("command_usage", entry, max_items=500)
        except Exception as e:
            logger.debug(f"Failed to record analytics for '{command_name}': {e}")
