# Desktop_Assistant/brain/engine/command_adapter.py
from __future__ import annotations

import inspect
import logging
import traceback
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("jarvis.command_adapter")


class CommandAdapter:
    """
    Lightweight adapter that normalizes different command module shapes.

    Constructor:
      CommandAdapter(func, name, metadata=None)

    Public API:
      - invoke(brain, user_text) -> dict with keys: success(bool), message(str), data(dict)
      - get_metadata() -> dict
      - name, timeout, aliases, category properties
    """

    def __init__(self, func: Callable[..., Any], name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.func = func
        self.name = (name or "").strip().lower()
        self.metadata = metadata or {}

        # Normalized metadata fields
        self.aliases = [a.lower() for a in (self.metadata.get("aliases") or []) if isinstance(a, str)]
        self.category = str(self.metadata.get("category") or "general")
        self.description = str(self.metadata.get("description") or "")
        self.os_support = [o.lower() for o in (self.metadata.get("os_support") or []) if isinstance(o, str)]
        # Optional per-command timeout (seconds)
        self.timeout = float(self.metadata.get("timeout")) if self.metadata.get("timeout") else None
        # Optional explicit disable flag (preferred over name-based checks)
        self.disabled = bool(self.metadata.get("disabled", False))

    # Metadata accessors
    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "aliases": list(self.aliases),
            "category": self.category,
            "description": self.description,
            "os_support": list(self.os_support),
            "timeout": self.timeout,
            "disabled": self.disabled,
        }

    # Backwards-compatible call surface
    def __call__(self, brain, query: str = "") -> Dict[str, Any]:
        return self.invoke(brain, query)

    def invoke(self, brain, query: str = "") -> Dict[str, Any]:
        """
        Invoke the underlying function and return a canonical dict:
          {"success": bool, "message": str, "data": dict}

        Behavior:
          - If metadata.disabled is True, returns blocked result.
          - Performs a best-effort safety check via brain.is_action_allowed (if available).
          - Calls the underlying function with one of these signatures:
              func(brain, query), func(query), func()
          - Normalizes return values and logs exceptions.
        """
        # 1) Disabled guard
        if self.disabled:
            logger.warning("Command '%s' is disabled via metadata.", self.name)
            return {"success": False, "message": "This command is disabled.", "data": {"blocked": True}}

        # 2) Adapter-level safety check (best-effort)
        try:
            if hasattr(brain, "detect_intent") and hasattr(brain, "is_action_allowed"):
                intent = brain.detect_intent(query)
                if intent is not None and not brain.is_action_allowed(query, intent):
                    logger.warning("Command '%s' blocked by safety (intent=%s).", self.name, intent)
                    return {"success": False, "message": "Action blocked by safety policy.", "data": {"blocked": True}}
        except Exception:
            logger.exception("Safety check failed for command '%s' (continuing).", self.name)

        # 3) Call the underlying function with flexible signature
        try:
            sig = inspect.signature(self.func)
            argc = len(sig.parameters)

            if argc >= 2:
                raw = self.func(brain, query)
            elif argc == 1:
                raw = self.func(query)
            else:
                raw = self.func()

            return self._normalize_result(raw)

        except Exception as exc:
            logger.exception("Command '%s' crashed during invoke: %s", self.name, exc)
            tb = traceback.format_exc()
            return {"success": False, "message": f"Command '{self.name}' failed.", "data": {"error": str(exc), "traceback": tb}}

    def _normalize_result(self, raw: Any) -> Dict[str, Any]:
        """
        Normalize return shapes into canonical dict:
          - dict -> used with defaults
          - bool -> success flag
          - str -> message
          - None -> success True, empty message
        """
        if raw is None:
            return {"success": True, "message": "", "data": {}}
        if isinstance(raw, dict):
            return {
                "success": bool(raw.get("success", True)),
                "message": str(raw.get("message", "")) if raw.get("message") is not None else "",
                "data": raw.get("data", {}) or {},
            }
        if isinstance(raw, bool):
            return {"success": raw, "message": "", "data": {}}
        return {"success": True, "message": str(raw), "data": {}}
