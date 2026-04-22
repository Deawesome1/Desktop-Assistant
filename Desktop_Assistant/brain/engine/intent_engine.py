# brain/engine/intent_engine.py

from typing import Any, Dict, List


class IntentEngine:
    def __init__(self, brain: "Brain") -> None:
        self.brain = brain

    def _score_intent_match(self, user_lower: str, intent: str, words: List[str]) -> float:
        score = 0.0
        for w in words:
            if w.lower() in user_lower:
                score += 1.0 + len(w) * 0.01
        if intent == "debugging" and ("error" in user_lower or "traceback" in user_lower):
            score += 0.5
        return score

    def detect_intent(self, text: str) -> str:
        user_lower = text.lower()
        keywords = self.brain.intent_cfg.get("detection", {}).get("keywords", {})

        best_intent = "unknown"
        best_score = 0.0

        for intent, words in keywords.items():
            score = self._score_intent_match(user_lower, intent, words)
            if score > best_score:
                best_score = score
                best_intent = intent

        if best_intent == "unknown":
            if "error" in user_lower or "traceback" in user_lower:
                return "debugging"
            if "architecture" in user_lower or "structure" in user_lower:
                return "architecture_design"
            if "brain.json" in user_lower or "brain architecture" in user_lower:
                return "brain_design"

        return best_intent
