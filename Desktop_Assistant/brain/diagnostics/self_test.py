"""
self_test.py — System-level diagnostic checks for the Brain.
"""

class SelfTest:
    def __init__(self, brain):
        self.brain = brain

    def run(self):
        """Return a structured diagnostic report."""
        return {
            "identity_loaded": bool(self.brain.identity),
            "drives_loaded": bool(self.brain.drives),
            "mood_engine_loaded": bool(self.brain.mood),
            "memory_config_loaded": bool(self.brain.memory_cfg),
            "context_engine_loaded": bool(self.brain.context),
            "intent_engine_loaded": bool(self.brain.intent_cfg),
            "command_cognition_loaded": bool(self.brain.command_cfg),
            "os_routing_loaded": bool(self.brain.os_routing_cfg),
            "app_scanner_loaded": bool(self.brain.app_scanner_cfg),
            "reasoning_loaded": bool(self.brain.reasoning_cfg),
            "speaker_loaded": bool(self.brain.speaker_cfg),
            "listener_loaded": bool(self.brain.listener_cfg),
            "safety_loaded": bool(self.brain.safety_cfg),

            # Runtime states
            "mood_runtime_state": dict(self.brain.mood_state),
            "context_runtime_state": dict(self.brain.conversation_state),
            "personality_runtime": dict(self.brain.personality_runtime),
            "drift_state": dict(self.brain._drift_state),
            "memory_category_counts": {
                k: len(v) for k, v in self.brain.memory_store.items()
            },

            # Commands
            "commands_loaded": list(self.brain.commands.keys()),
            "aliases_registered": list(self.brain.alias_map.keys()),
        }
