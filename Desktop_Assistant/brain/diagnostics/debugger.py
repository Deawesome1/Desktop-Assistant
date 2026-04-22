"""
debugger.py — Debug snapshot + pretty print for the Brain.
"""

class Debugger:
    def __init__(self, brain):
        self.brain = brain

    def snapshot(self):
        """Return a structured snapshot of the Brain's current runtime state."""
        return {
            "identity_name": self.brain.get_display_name(),
            "mood": dict(self.brain.mood_state),
            "personality_runtime": dict(self.brain.personality_runtime),
            "context": dict(self.brain.conversation_state),
            "drift_state": dict(self.brain._drift_state),
            "memory_categories": {
                k: len(v) for k, v in self.brain.memory_store.items()
            },
            "commands_loaded": list(self.brain.commands.keys()),
            "aliases_registered": list(self.brain.alias_map.keys()),
        }

    def print(self):
        """Pretty-print the snapshot."""
        snap = self.snapshot()
        print("\n=== BRAIN DEBUG SNAPSHOT ===")
        for key, value in snap.items():
            print(f"{key}: {value}")
        print("=== END DEBUG ===\n")
