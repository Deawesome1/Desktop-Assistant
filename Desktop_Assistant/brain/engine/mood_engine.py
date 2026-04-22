# brain/engine/mood_engine.py

import time
from typing import Any, Dict

class MoodEngine:
    def __init__(self, brain: "Brain") -> None:
        self.brain = brain

    def get_mood(self) -> Dict[str, float]:
        return dict(self.brain.mood_state)

    def apply_mood_event(self, event: str) -> None:
        rules = self.brain.mood.get("modulation_rules", {})
        delta = rules.get(event)
        if not delta:
            return

        for key, change in delta.items():
            if key.endswith("_delta"):
                mood_key = key.replace("_delta", "")
                current = self.brain.mood_state.get(mood_key, 0.0)
                self.brain.mood_state[mood_key] = max(
                    0.0, min(1.0, current + float(change))
                )

    def decay_mood(self, factor: float = 0.02, interval: float = 60.0) -> None:
        now = time.time()
        if now - self.brain._last_mood_decay < interval:
            return
        self.brain._last_mood_decay = now

        baseline = self.brain.mood.get("state", {})
        for key, base_val in baseline.items():
            current = self.brain.mood_state.get(key, base_val)
            self.brain.mood_state[key] = current + (base_val - current) * factor
