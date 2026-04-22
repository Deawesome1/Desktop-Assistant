# brain/engine/personality_engine.py

import time
from typing import Any, Dict


class PersonalityEngine:
    def __init__(self, brain: "Brain") -> None:
        self.brain = brain

    def register_interaction(self, success: bool, frustrated_user: bool = False) -> None:
        self.brain._drift_state["interactions"] += 1
        if success:
            self.brain._drift_state["successes"] += 1
        if frustrated_user:
            self.brain._drift_state["frustrations"] += 1

        if success:
            self.brain.apply_mood_event("on_successful_breakthrough")
        if frustrated_user:
            self.brain.apply_mood_event("on_user_confusion")

        self._apply_personality_drift()

    def _apply_personality_drift(self) -> None:
        interactions = max(1, self.brain._drift_state["interactions"])
        success_rate = self.brain._drift_state["successes"] / interactions
        frustration_rate = self.brain._drift_state["frustrations"] / interactions

        base = self.brain.identity.get("style", {})

        def clamp(v: float) -> float:
            return max(0.0, min(1.0, v))

        self.brain.personality_runtime["warmth"] = clamp(
            base.get("warmth", 0.72) + (success_rate - frustration_rate) * 0.1
        )
        self.brain.personality_runtime["humor_level"] = clamp(
            base.get("humor_level", 0.35) + (success_rate - frustration_rate) * 0.05
        )
        self.brain.personality_runtime["sarcasm_level"] = clamp(
            base.get("sarcasm_level", 0.18) + (frustration_rate - success_rate) * 0.05
        )
        self.brain.personality_runtime["directness"] = clamp(
            base.get("directness", 0.9) + frustration_rate * 0.05
        )

    def decay_personality(self, factor: float = 0.02, interval: float = 300.0) -> None:
        now = time.time()
        if now - self.brain._last_personality_decay < interval:
            return
        self.brain._last_personality_decay = now

        base = self.brain.identity.get("style", {})
        for key, base_val in base.items():
            if isinstance(base_val, (int, float)):
                current = self.brain.personality_runtime.get(key, base_val)
                self.brain.personality_runtime[key] = current + (base_val - current) * factor
