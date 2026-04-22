"""
brain.py — Core brain engine for JARVIS (Omega)

Clean, corrected, stable version.
Ensures proper initialization order, OS routing, dependency loading,
subsystem setup, and modular command loading.
"""

import json
import os
import platform
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..dependency_manager import ensure
from ..loader import CommandLoader

from .mood_engine import MoodEngine
from .personality_engine import PersonalityEngine
from .memory_engine import MemoryEngine
from .context_engine import ContextEngine
from .intent_engine import IntentEngine
from .safety_engine import SafetyEngine
from .os_router import OSRouter


class BrainConfigError(Exception):
    pass


class Brain:
    def __init__(self, config_path: str = "config/brain.json") -> None:
        # ------------------------------------------------------------------
        # Load OS routing config (raw JSON)
        # ------------------------------------------------------------------
        self.os_routing_cfg = self.load_json("os_routing.json")

        # Resolve config path relative to Desktop_Assistant root
        base = Path(__file__).resolve().parents[2]
        self.config_path = str(base / config_path)

        # Internal config + flags
        self._config: Dict[str, Any] = {}
        self._loaded = False

        # Cached config subtrees
        self.identity = {}
        self.drives = {}
        self.mood = {}
        self.memory_cfg = {}
        self.memory_store = {}

        self.context = {}
        self.intent_cfg = {}
        self.command_cfg = {}
        self.app_scanner_cfg = {}
        self.reasoning_cfg = {}
        self.speaker_cfg = {}
        self.listener_cfg = {}
        self.safety_cfg = {}

        # Runtime state
        self.mood_state = {}
        self.conversation_state = {}

        # Personality drift runtime state
        self._drift_state = {"interactions": 0, "successes": 0, "frustrations": 0}
        self.personality_runtime = {}

        # Decay timers
        now = time.time()
        self._last_mood_decay = now
        self._last_personality_decay = now

        # Command registry
        self.commands: Dict[str, Any] = {}
        self.alias_map: Dict[str, str] = {}

        # Subsystem placeholders
        self.mood_engine = None
        self.personality_engine = None
        self.memory_engine = None
        self.context_engine = None
        self.intent_engine = None
        self.safety_engine = None

        # ------------------------------------------------------------------
        # ⭐ FIX: Initialize OSRouter FIRST (must receive Brain instance)
        # ------------------------------------------------------------------
        self.os_router = OSRouter(self)

        # ------------------------------------------------------------------
        # ⭐ FIX: Now dependencies can be safely checked
        # ------------------------------------------------------------------
        self.ensure_dependencies()

        # ------------------------------------------------------------------
        # Load config + bind subtrees + init runtime state
        # ------------------------------------------------------------------
        self.load()

        # ------------------------------------------------------------------
        # Initialize subsystem engines
        # ------------------------------------------------------------------
        self._init_subsystems()

        # ------------------------------------------------------------------
        # Load commands via modular loader
        # ------------------------------------------------------------------
        self._load_commands_modular()

    # ======================================================================
    # DEPENDENCIES
    # ======================================================================

    def ensure_dependencies(self) -> None:
        ensure("psutil")
        ensure("pillow")
        ensure("pyautogui")
        ensure("requests")

        if self.get_current_os_key() == "windows":
            ensure("pycaw")
            ensure("comtypes")

    # ======================================================================
    # CONFIG LOADING
    # ======================================================================

    def load(self) -> None:
        if not os.path.exists(self.config_path):
            raise BrainConfigError(f"brain.json not found at {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

        self._loaded = True
        self._bind_subtrees()
        self._init_runtime_state()

    def _bind_subtrees(self) -> None:
        self.identity = self._config.get("identity", {})
        self.drives = self._config.get("drives", {})
        self.mood = self._config.get("mood_engine", {})
        self.memory_cfg = self._config.get("memory", {})
        self.context = self._config.get("context_engine", {})
        self.intent_cfg = self._config.get("intent_engine", {})
        self.command_cfg = self._config.get("command_cognition", {})
        self.os_routing_cfg = self._config.get("os_routing", self.os_routing_cfg)
        self.app_scanner_cfg = self._config.get("app_scanner", {})
        self.reasoning_cfg = self._config.get("reasoning", {})
        self.speaker_cfg = self._config.get("speaker", {})
        self.listener_cfg = self._config.get("listener", {})
        self.safety_cfg = self._config.get("safety", {})

    def _init_runtime_state(self) -> None:
        self.mood_state = dict(self.mood.get("state", {}))
        self.conversation_state = dict(self.context.get("conversation_state", {}))

        style = self.identity.get("style", {})
        self.personality_runtime = {
            "humor_level": style.get("humor_level", 0.35),
            "sarcasm_level": style.get("sarcasm_level", 0.18),
            "warmth": style.get("warmth", 0.72),
            "directness": style.get("directness", 0.9),
        }

        self.memory_store = {}

        now = time.time()
        self._last_mood_decay = now
        self._last_personality_decay = now

    # ======================================================================
    # SUBSYSTEM INITIALIZATION
    # ======================================================================

    def _init_subsystems(self) -> None:
        self.mood_engine = MoodEngine(self)
        self.personality_engine = PersonalityEngine(self)
        self.memory_engine = MemoryEngine(self)
        self.context_engine = ContextEngine(self)
        self.intent_engine = IntentEngine(self)
        self.safety_engine = SafetyEngine(self)

    # ======================================================================
    # COMMAND LOADING
    # ======================================================================

    def _load_commands_modular(self):
        os_key = self.get_current_os_key()
        loader = CommandLoader(os_key)
        self.commands, self.alias_map = loader.load_all()

    def load_all_command_modules(self):
        return self.commands

    # ======================================================================
    # COMMAND LOOKUP
    # ======================================================================

    def find_command(self, user_text: str) -> Optional[Any]:
        text = user_text.lower().strip()

        if text in self.commands:
            return self.commands.get(text)

        for alias, name_key in self.alias_map.items():
            if alias in text:
                return self.commands.get(name_key)

        return None

    # ======================================================================
    # OS ROUTING
    # ======================================================================

    def get_os_mapping(self) -> Dict[str, str]:
        return self.os_router.get_os_mapping()

    def get_current_os_key(self) -> str:
        return self.os_router.get_current_os_key()

    # ======================================================================
    # MEMORY ENGINE WRAPPERS
    # ======================================================================

    def remember(self, category, item, max_items=None, salience=None):
        if self.memory_engine:
            return self.memory_engine.remember(category, item, max_items, salience)

    def recall(self, category, limit=None):
        if self.memory_engine:
            return self.memory_engine.recall(category, limit)
        return []

    def save_memory(self, path="config/memory_store.json"):
        if self.memory_engine:
            return self.memory_engine.save_memory(path)

    def load_memory(self, path="config/memory_store.json"):
        if self.memory_engine:
            return self.memory_engine.load_memory(path)

    # ======================================================================
    # JSON LOADING
    # ======================================================================

    def load_json(self, filename):
        base = Path(__file__).resolve().parent
        path = base / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing required config file: {path}")
        with open(path, "r") as f:
            return json.load(f)

    # ======================================================================
    # PERSONALITY DRIFT
    # ======================================================================

    def register_interaction(self, success, frustrated_user=False):
        if self.personality_engine:
            return self.personality_engine.register_interaction(success, frustrated_user)

    def decay_personality(self, factor=0.02, interval=300.0):
        if self.personality_engine:
            return self.personality_engine.decay_personality(factor, interval)

    # ======================================================================
    # MOOD ENGINE
    # ======================================================================

    def get_mood(self):
        if self.mood_engine:
            return self.mood_engine.get_mood()
        return dict(self.mood_state)

    def apply_mood_event(self, event):
        if self.mood_engine:
            return self.mood_engine.apply_mood_event(event)

    def decay_mood(self, factor=0.02, interval=60.0):
        if self.mood_engine:
            return self.mood_engine.decay_mood(factor, interval)

    # ======================================================================
    # CONTEXT ENGINE
    # ======================================================================

    def get_context(self):
        if self.context_engine:
            return self.context_engine.get_context()
        return dict(self.conversation_state)

    def set_current_topic(self, topic):
        if self.context_engine:
            return self.context_engine.set_current_topic(topic)

    def set_current_project(self, project):
        if self.context_engine:
            return self.context_engine.set_current_project(project)

    def set_last_command(self, name):
        if self.context_engine:
            return self.context_engine.set_last_command(name)

    def add_touched_file(self, path):
        if self.context_engine:
            return self.context_engine.add_touched_file(path)

    # ======================================================================
    # INTENT ENGINE
    # ======================================================================

    def detect_intent(self, text):
        if self.intent_engine:
            return self.intent_engine.detect_intent(text)
        return "unknown"

    # ======================================================================
    # SAFETY ENGINE
    # ======================================================================

    def get_safety_limits(self):
        if self.safety_engine:
            return self.safety_engine.get_safety_limits()
        return self.safety_cfg.get("hard_limits", {})

    def is_action_allowed(self, text, action_type):
        if self.safety_engine:
            return self.safety_engine.is_action_allowed(text, action_type)
        return True

    # ======================================================================
    # EVENTS
    # ======================================================================

    def event(self, name, *args):
        name = name.lower()

        if name == "user_confused":
            self.register_interaction(success=False, frustrated_user=True)
            self.apply_mood_event("on_user_confusion")

        elif name == "task_success":
            self.register_interaction(success=True, frustrated_user=False)
            self.apply_mood_event("on_successful_breakthrough")

        elif name == "topic_change" and args:
            self.set_current_topic(str(args[0]))

        elif name == "remember_text" and len(args) >= 2:
            self.remember(str(args[0]), str(args[1]))

        elif name == "project_change" and args:
            self.set_current_project(str(args[0]))

    # ======================================================================
    # UTILITY
    # ======================================================================

    def reload(self):
        self.load()
        self._init_subsystems()
        self._load_commands_modular()

    def to_dict(self):
        out = dict(self._config)
        out.setdefault("mood_engine_runtime", {})["state"] = dict(self.mood_state)
        out.setdefault("context_engine_runtime", {})["conversation_state"] = dict(self.conversation_state)
        out.setdefault("personality_runtime", {}).update(self.personality_runtime)
        out.setdefault("drift_state", {}).update(self._drift_state)
        return out

    # ======================================================================
    # DEBUGGING
    # ======================================================================

    def debug_snapshot(self):
        return {
            "identity_name": self.get_display_name(),
            "mood": dict(self.mood_state),
            "personality_runtime": dict(self.personality_runtime),
            "context": dict(self.conversation_state),
            "drift_state": dict(self._drift_state),
            "memory_categories": {k: len(v) for k, v in self.memory_store.items()},
            "commands_loaded": list(self.commands.keys()),
        }

    def debug_print(self):
        snap = self.debug_snapshot()
        print("\n=== BRAIN DEBUG SNAPSHOT ===")
        for key, value in snap.items():
            print(f"{key}: {value}")
        print("=== END DEBUG ===\n")

    # ======================================================================
    # SELF TEST
    # ======================================================================

    def self_test(self):
        return {
            "identity_loaded": bool(self.identity),
            "drives_loaded": bool(self.drives),
            "mood_engine_loaded": bool(self.mood),
            "memory_config_loaded": bool(self.memory_cfg),
            "context_engine_loaded": bool(self.context),
            "intent_engine_loaded": bool(self.intent_cfg),
            "command_cognition_loaded": bool(self.command_cfg),
            "os_routing_loaded": bool(self.os_routing_cfg),
            "app_scanner_loaded": bool(self.app_scanner_cfg),
            "reasoning_loaded": bool(self.reasoning_cfg),
            "speaker_loaded": bool(self.speaker_cfg),
            "listener_loaded": bool(self.listener_cfg),
            "safety_loaded": bool(self.safety_cfg),
            "mood_runtime_state": dict(self.mood_state),
            "context_runtime_state": dict(self.conversation_state),
            "personality_runtime": dict(self.personality_runtime),
            "drift_state": dict(self._drift_state),
            "memory_category_counts": {k: len(v) for k, v in self.memory_store.items()},
            "commands_loaded": list(self.commands.keys()),
            "aliases_registered": list(self.alias_map.keys()),
        }


# Singleton accessor
_global_brain: Optional[Brain] = None
