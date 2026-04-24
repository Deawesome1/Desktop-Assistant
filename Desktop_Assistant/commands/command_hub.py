# Desktop_Assistant/commands/command_hub.py
"""
CommandHub — full production-ready implementation.

Features
- Adapter-first execution (CommandAdapter.invoke)
- Fallback support for legacy modules and loader placeholders
- Per-command timeout enforced with a worker thread
- Centralized logging and file handler
- Analytics recording via brain.remember
- Hooks for chaining and pipelines (post-execution speak hook implemented)
"""

from __future__ import annotations

import os
import time
import logging
import threading
from typing import Any, Dict, Optional

from Desktop_Assistant import imports as I
from Desktop_Assistant.bot.speaker import speak_async

Brain = I.Brain

# ----------------------------------------------------------------------
# Logger
# ----------------------------------------------------------------------
LOGGER_NAME = "jarvis.command_hub"


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    os.makedirs("logs", exist_ok=True)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [Hub] %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(ch)

    fh = logging.FileHandler("logs/command_hub.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(fh)

    return logger


logger = _setup_logger()

# ----------------------------------------------------------------------
# CommandHub
# ----------------------------------------------------------------------
DEFAULT_COMMAND_TIMEOUT = 10.0  # seconds


class CommandHub:
    def __init__(
        self,
        brain: Brain,
        debug: bool = False,
        dry_run: bool = False,
        command_timeout: Optional[float] = None,
    ):
        self.brain = brain
        self.debug = debug
        self.dry_run = dry_run
        self.command_timeout = command_timeout or DEFAULT_COMMAND_TIMEOUT
        if self.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("CommandHub initialized in DEBUG mode.")
        else:
            logger.debug("CommandHub initialized.")

    # Public API
    def handle(self, user_text: str) -> Dict[str, Any]:
        return self.execute(user_text)

    def execute(self, user_text: str) -> Dict[str, Any]:
        start_time = time.time()
        os_key = self.brain.get_current_os_key()
        intent = self.brain.detect_intent(user_text)

        if self.debug:
            logger.debug("Incoming text: %r", user_text)
            logger.debug("Detected intent: %s", intent)
            logger.debug("OS key: %s", os_key)

        # Safety check
        if not self.brain.is_action_allowed(user_text, intent):
            logger.warning("Blocked unsafe action. Intent=%s, text=%r", intent, user_text)
            self.brain.event("user_confused")
            return self._build_response(
                False,
                "I can't help with that.",
                {"blocked": True, "intent": intent, "reason": "safety_limits"},
                start_time,
                None,
                error_type="safety_block",
            )

        # Command lookup
        command_obj = self.brain.find_command(user_text)
        if not command_obj:
            logger.info("No command matched for text: %r", user_text)
            self.brain.event("user_confused")
            return self._build_response(
                False,
                "I didn't understand that command.",
                {"matched": False, "intent": intent},
                start_time,
                None,
                error_type="no_match",
            )

        # Metadata
        meta = self._get_command_metadata(command_obj)
        command_name = meta.get("name", "unknown")
        aliases = meta.get("aliases", [])
        category = meta.get("category", "general")

        if self.debug:
            logger.debug("Matched command: %s (category=%s, aliases=%s)", command_name, category, aliases)

        # Update context
        try:
            self.brain.set_last_command(command_name)
        except Exception:
            logger.debug("set_last_command failed for %s", command_name)

        # Dry-run
        if self.dry_run:
            logger.info("DRY RUN: would execute command '%s'", command_name)
            return self._build_response(
                True,
                f"(Dry run) Would execute command '{command_name}'.",
                {"dry_run": True, "command": command_name, "intent": intent, "category": category},
                start_time,
                command_name,
            )

        # Execute with timeout and normalization
        try:
            timeout = getattr(command_obj, "timeout", None) or self.command_timeout
            raw_result = self._invoke_with_timeout(command_obj, user_text, timeout)
            result = self._normalize_raw_result(raw_result)

            success = bool(result.get("success", False))
            if success:
                self.brain.event("task_success")
                logger.info("Command '%s' succeeded.", command_name)
            else:
                self.brain.event("user_confused")
                logger.warning("Command '%s' reported failure.", command_name)

            # Hook: post-execution pipeline (speaking, telemetry, chaining)
            try:
                self._post_execution_hook(command_name, result)
            except Exception:
                logger.debug("Post execution hook failed for %s", command_name)

            return self._build_response(
                success,
                result.get("message", ""),
                result.get("data", {}),
                start_time,
                command_name,
                intent=intent,
                category=category,
            )

        except Exception as exc:
            logger.exception("Command '%s' crashed: %s", command_name, exc)
            self.brain.event("user_confused")
            return self._build_response(
                False,
                f"Command '{command_name}' failed.",
                {"error": str(exc)},
                start_time,
                command_name,
                intent=intent,
                category=category,
                error_type="exception",
            )

    # Invocation helpers
    def _get_command_metadata(self, command_obj) -> Dict[str, Any]:
        # Adapter style
        if hasattr(command_obj, "get_metadata") and callable(getattr(command_obj, "get_metadata")):
            meta = command_obj.get_metadata() or {}
            return {
                "name": meta.get("name") or getattr(command_obj, "name", None),
                "aliases": meta.get("aliases", []) or getattr(command_obj, "aliases", []),
                "category": meta.get("category") or getattr(command_obj, "category", "general"),
            }

        # Fallback wrapper
        if isinstance(command_obj, dict):
            meta = command_obj.get("metadata") or {}
            return {
                "name": meta.get("name") or command_obj.get("name"),
                "aliases": meta.get("aliases") or [],
                "category": meta.get("category") or "general",
            }

        # Legacy module
        try:
            getter = getattr(command_obj, "get_metadata", None)
            if callable(getter):
                m = getter() or {}
                return {
                    "name": m.get("name") or getattr(command_obj, "__name__", "unknown"),
                    "aliases": m.get("aliases", []),
                    "category": m.get("category", "general"),
                }
        except Exception:
            pass

        return {
            "name": getattr(command_obj, "name", getattr(command_obj, "__name__", "unknown")),
            "aliases": [],
            "category": "general",
        }

    def _invoke_with_timeout(self, command_obj, user_text: str, timeout: float):
        container = {"result": None, "exc": None}

        def target():
            try:
                # Adapter interface
                if hasattr(command_obj, "invoke") and callable(getattr(command_obj, "invoke")):
                    container["result"] = command_obj.invoke(self.brain, user_text)
                    return
                # Fallback wrapper
                if isinstance(command_obj, dict) and callable(command_obj.get("callable")):
                    container["result"] = command_obj["callable"](self.brain, user_text)
                    return
                # Legacy module
                for attr in ("run", "execute", "main"):
                    fn = getattr(command_obj, attr, None)
                    if callable(fn):
                        container["result"] = fn(self.brain, user_text)
                        return
                raise RuntimeError("Unsupported command object shape")
            except Exception as e:
                container["exc"] = e

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            logger.warning("Command invocation timed out after %.1fs", timeout)
            return {"success": False, "message": "Command timed out.", "data": {}, "error_type": "timeout"}

        if container["exc"]:
            raise container["exc"]

        return container["result"]

    def _normalize_raw_result(self, raw_result) -> Dict[str, Any]:
        if raw_result is None:
            return {"success": True, "message": "", "data": {}}
        if isinstance(raw_result, dict):
            return {
                "success": bool(raw_result.get("success", True)),
                "message": str(raw_result.get("message", "")) if raw_result.get("message") is not None else "",
                "data": raw_result.get("data", {}) or {},
            }
        if isinstance(raw_result, bool):
            return {"success": raw_result, "message": "", "data": {}}
        return {"success": True, "message": str(raw_result), "data": {}}

    # Post execution hook for chaining/pipelines and speaking
    def _post_execution_hook(self, command_name: str, result: Dict[str, Any]) -> None:
        """
        After a command finishes, optionally speak the result message asynchronously.
        Respects:
          - command-level metadata 'speak': False to suppress speaking
          - global brain setting 'voice_speaking_enabled' (defaults to True)
        """
        try:
            # Determine speak permission from result meta first, then fallback to command metadata
            speak_allowed = True
            if isinstance(result, dict):
                meta = result.get("meta", {}) or {}
                if "speak" in meta:
                    speak_allowed = bool(meta.get("speak"))
            # If result didn't include meta.speak, try to read command metadata from brain (best-effort)
            if speak_allowed:
                try:
                    # brain may expose a way to fetch last command metadata; attempt best-effort
                    cmd_meta = {}
                    try:
                        # If the command registry stores metadata, try to fetch it
                        cmd_meta = self.brain.get_command_metadata(command_name) if hasattr(self.brain, "get_command_metadata") else {}
                    except Exception:
                        cmd_meta = {}
                    if cmd_meta and "speak" in cmd_meta:
                        speak_allowed = bool(cmd_meta.get("speak"))
                except Exception:
                    # ignore and proceed with previous speak_allowed value
                    pass

            if not speak_allowed:
                logger.debug("Skipping speak for %s because speak_allowed is False", command_name)
                return

            # Extract message to speak
            message = ""
            if isinstance(result, dict):
                message = result.get("message") or (result.get("data") or {}).get("message", "") or ""
            if not message:
                # nothing to speak
                return

            # Check global toggle in brain settings or memory
            enabled = True
            try:
                enabled = self.brain.get_setting("voice_speaking_enabled", True)
            except Exception:
                try:
                    mem = getattr(self.brain, "memory", None)
                    if mem and isinstance(mem.get("voice_speaking_enabled"), bool):
                        enabled = mem.get("voice_speaking_enabled")
                except Exception:
                    enabled = True

            if not enabled:
                logger.debug("Global voice speaking disabled; not speaking result for %s", command_name)
                return

            # Speak asynchronously so hub is non-blocking
            logger.debug("Speaking result for %s: %s", command_name, message)
            try:
                speak_async(message, brain=self.brain)
            except Exception:
                logger.exception("speak_async failed for %s", command_name)

        except Exception:
            logger.exception("Post execution speak hook failed for %s", command_name)

    # Response builder and analytics
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

        if command_name:
            if success:
                logger.info(
                    "Command '%s' completed in %.3fs (intent=%s, category=%s)", command_name, elapsed, intent, category
                )
            else:
                logger.warning(
                    "Command '%s' failed in %.3fs (intent=%s, category=%s, error_type=%s)",
                    command_name,
                    elapsed,
                    intent,
                    category,
                    error_type,
                )
        else:
            if success:
                logger.info("Non-command response in %.3fs", elapsed)
            else:
                logger.warning("Non-command failure in %.3fs (error_type=%s)", elapsed, error_type)

        # Analytics
        try:
            if command_name:
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
        except Exception:
            logger.debug("Failed to record analytics for '%s'", command_name)

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
