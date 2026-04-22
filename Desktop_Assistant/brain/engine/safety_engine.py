# brain/engine/safety_engine.py

import re
from typing import Any, Dict


class SafetyEngine:
    def __init__(self, brain: "Brain") -> None:
        self.brain = brain

    def get_safety_limits(self):
        return self.brain.safety_cfg.get("hard_limits", {})

    def is_action_allowed(self, text: str, action_type: str) -> bool:
        limits = self.get_safety_limits()
        text_lower = text.lower()

        if action_type in ("shutdown", "restart", "format_disk"):
            if limits.get("no_harm_to_others", True):
                return False

        if limits.get("no_self_harm", True):
            if re.search(r"\bkill myself\b|\bsuicide\b", text_lower):
                return False

        if limits.get("no_illegal_instructions", True):
            if "how do i hack" in text_lower or "bypass" in text_lower:
                return False

        return True
