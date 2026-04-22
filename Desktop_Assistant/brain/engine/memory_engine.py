# brain/engine/memory_engine.py

import json
import os
from typing import Any, Dict, List, Optional


class MemoryEngine:
    def __init__(self, brain: "Brain") -> None:
        self.brain = brain

    def _classify_salience(self, text: str) -> str:
        rules = self.brain.memory_cfg.get("salience_rules", {})
        text_lower = text.lower()

        def matches_any(patterns):
            return any(p.lower() in text_lower for p in patterns)

        if matches_any(rules.get("high_salience", [])):
            return "high_salience"
        if matches_any(rules.get("medium_salience", [])):
            return "medium_salience"
        return "low_salience"

    def remember(self, category, item, max_items=None, salience=None):
        if salience is None:
            salience = (
                self._classify_salience(item) if isinstance(item, str) else "medium_salience"
            )

        cat_cfg = (
            self.brain.memory_cfg.get("long_term", {})
            .get("categories", {})
            .get(category, {})
        )
        limit = max_items or cat_cfg.get("max_items", 100)

        bucket = self.brain.memory_store.setdefault(category, [])
        bucket.append(item)
        if len(bucket) > limit:
            self.brain.memory_store[category] = bucket[-limit:]

    def recall(self, category, limit=None):
        bucket = self.brain.memory_store.get(category, [])
        return bucket[-limit:] if limit else list(bucket)

    def save_memory(self, path="config/memory_store.json"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.brain.memory_store, f, indent=2)

    def load_memory(self, path="config/memory_store.json"):
        if os.path.exists(path):
            with open(path, "r") as f:
                self.brain.memory_store = json.load(f)
