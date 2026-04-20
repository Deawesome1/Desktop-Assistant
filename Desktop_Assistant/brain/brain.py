"""
brain.py — Core brain engine for JARVIS (Omega)

Loads brain.json and exposes:
    - Brain: main facade
    - access to identity, drives, mood, memory, context, intent, commands, etc.
    - personality drift engine
    - memory engine (runtime + persistence)
    - debugger, self-diagnostics, event system, decay
"""

import json
import os
import platform
import re
import time
import importlib
from typing import Any, Dict, List, Optional
from dependency_manager import ensure


class BrainConfigError(Exception):
    pass


class Brain:
    def __init__(self, config_path: str = "config/brain.json") -> None:
        self.ensure_dependencies()
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self._loaded = False

        # Cached subtrees
        self.identity: Dict[str, Any] = {}
        self.drives: Dict[str, Any] = {}
        self.mood: Dict[str, Any] = {}
        self.memory_cfg: Dict[str, Any] = {}
        self.memory_store: Dict[str, List[Any]] = {}

        self.context: Dict[str, Any] = {}
        self.intent_cfg: Dict[str, Any] = {}
        self.command_cfg: Dict[str, Any] = {}
        self.os_routing_cfg: Dict[str, Any] = {}
        self.app_scanner_cfg: Dict[str, Any] = {}
        self.reasoning_cfg: Dict[str, Any] = {}
        self.speaker_cfg: Dict[str, Any] = {}
        self.listener_cfg: Dict[str, Any] = {}
        self.safety_cfg: Dict[str, Any] = {}

        # Runtime state (mutable)
        self.mood_state: Dict[str, float] = {}
        self.conversation_state: Dict[str, Any] = {}

        # Personality / drift runtime state
        self._drift_state = {
            "interactions": 0,
            "successes": 0,
            "frustrations": 0,
        }
        self.personality_runtime: Dict[str, float] = {}

        # Decay timing
        self._last_mood_decay: float = time.time()
        self._last_personality_decay: float = time.time()

        # Command registry
        self.commands: Dict[str, Any] = {}      # command_name -> module
        self.alias_map: Dict[str, str] = {}     # alias -> command_name

        self.load()
        self.load_commands()

    def ensure_dependencies(self):
        ensure("psutil")
        ensure("PIL")
        ensure("pyautogui")
        ensure("requests")

        # Windows-only
        if self.get_current_os_key() == "windows":
            ensure("pycaw")
            ensure("comtypes")

    # -------------------------------------------------------------------------
    # Loading / basic access
    # -------------------------------------------------------------------------

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
        self.os_routing_cfg = self._config.get("os_routing", {})
        self.app_scanner_cfg = self._config.get("app_scanner", {})
        self.reasoning_cfg = self._config.get("reasoning", {})
        self.speaker_cfg = self._config.get("speaker", {})
        self.listener_cfg = self._config.get("listener", {})
        self.safety_cfg = self._config.get("safety", {})

    def _init_runtime_state(self) -> None:
        # Mood runtime state
        self.mood_state = dict(self.mood.get("state", {}))

        # Conversation runtime state
        self.conversation_state = dict(self.context.get("conversation_state", {}))

        # Personality / drift runtime state (runtime overlay of style)
        style = self.identity.get("style", {})
        self.personality_runtime = {
            "humor_level": style.get("humor_level", 0.35),
            "sarcasm_level": style.get("sarcasm_level", 0.18),
            "warmth": style.get("warmth", 0.72),
            "directness": style.get("directness", 0.9),
        }

        # Initialize memory store
        self.memory_store = {}

        # Reset decay timers
        now = time.time()
        self._last_mood_decay = now
        self._last_personality_decay = now

    # -------------------------------------------------------------------------
    # Command loading / awareness
    # -------------------------------------------------------------------------

    def load_commands(self, commands_package: str = "commands") -> None:
        """
        Scan the commands/ folder, import all command modules, and register
        OS-appropriate commands + aliases.
        """
        # commands/ is sibling to brain/ at project root
        root_dir = os.path.dirname(os.path.dirname(__file__))
        commands_dir = os.path.join(root_dir, commands_package)

        if not os.path.isdir(commands_dir):
            return

        os_key = self.get_current_os_key()

        for file in os.listdir(commands_dir):
            if not file.endswith(".py") or file.startswith("__"):
                continue

            module_name = file[:-3]
            module_path = f"{commands_package}.{module_name}"

            try:
                module = importlib.import_module(module_path)
            except Exception as e:
                print(f"[Brain] Failed to import {module_path}: {e}")
                continue

            if not hasattr(module, "get_metadata") or not hasattr(module, "run"):
                continue

            try:
                meta = module.get_metadata()
            except Exception as e:
                print(f"[Brain] Failed to read metadata from {module_path}: {e}")
                continue

            # OS filtering
            os_support = meta.get("os_support", [])
            if os_support and os_key not in os_support:
                continue

            name = meta.get("name")
            if not name:
                continue

            self.commands[name] = module

            for alias in meta.get("aliases", []):
                if not isinstance(alias, str):
                    continue
                self.alias_map[alias.lower()] = name

    def find_command(self, user_text: str) -> Optional[Any]:
        """
        Given raw user text, find the best-matching command module based on aliases.
        """
        text = user_text.lower()

        # Simple alias containment match
        for alias, name in self.alias_map.items():
            if alias in text:
                return self.commands.get(name)

        return None

    # -------------------------------------------------------------------------
    # Identity / style
    # -------------------------------------------------------------------------

    def get_display_name(self) -> str:
        return self.identity.get("display_name", "Assistant")

    def get_style(self) -> Dict[str, Any]:
        return self.identity.get("style", {})

    # -------------------------------------------------------------------------
    # Memory engine (runtime + simple persistence + salience)
    # -------------------------------------------------------------------------

    def _classify_salience(self, text: str) -> str:
        """
        Use brain.json salience rules to classify a piece of text as
        'high_salience', 'medium_salience', or 'low_salience'.
        """
        salience_rules = self.memory_cfg.get("salience_rules", {})
        text_lower = text.lower()

        def matches_any(patterns: List[str]) -> bool:
            for p in patterns:
                if p.lower() in text_lower:
                    return True
            return False

        if matches_any(salience_rules.get("high_salience", [])):
            return "high_salience"
        if matches_any(salience_rules.get("medium_salience", [])):
            return "medium_salience"
        return "low_salience"

    def remember(
        self,
        category: str,
        item: Any,
        max_items: Optional[int] = None,
        salience: Optional[str] = None,
    ) -> None:
        """
        Store an item in a memory category. Uses brain.json limits if available.
        Optionally uses salience to decide whether to store or not.
        """
        if salience is None and isinstance(item, str):
            salience = self._classify_salience(item)
        elif salience is None:
            salience = "medium_salience"

        # Example: ignore low-salience items for some categories
        if salience == "low_salience" and category not in ("user_preferences",):
            pass

        cat_cfg = (
            self.memory_cfg
            .get("long_term", {})
            .get("categories", {})
            .get(category, {})
        )
        limit = max_items or cat_cfg.get("max_items", 100)

        bucket = self.memory_store.setdefault(category, [])
        bucket.append(item)
        if len(bucket) > limit:
            self.memory_store[category] = bucket[-limit:]

    def recall(self, category: str, limit: Optional[int] = None) -> List[Any]:
        """
        Return up to `limit` most recent items from a category.
        """
        bucket = self.memory_store.get(category, [])
        if limit is None:
            return list(bucket)
        return bucket[-limit:]

    def save_memory(self, path: str = "config/memory_store.json") -> None:
        """
        Persist runtime memory to disk.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.memory_store, f, indent=2)

    def load_memory(self, path: str = "config/memory_store.json") -> None:
        """
        Load runtime memory from disk if present.
        """
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            self.memory_store = data

    # -------------------------------------------------------------------------
    # Personality drift engine
    # -------------------------------------------------------------------------

    def register_interaction(self, success: bool, frustrated_user: bool = False) -> None:
        """
        Call this after each interaction to feed the drift engine.
        success=True when the user seems satisfied.
        frustrated_user=True when the user seems annoyed/confused.
        """
        self._drift_state["interactions"] += 1
        if success:
            self._drift_state["successes"] += 1
        if frustrated_user:
            self._drift_state["frustrations"] += 1

        if success:
            self.apply_mood_event("on_successful_breakthrough")
        if frustrated_user:
            self.apply_mood_event("on_user_confusion")

        self._apply_personality_drift()

    def _apply_personality_drift(self) -> None:
        """
        Slowly adjusts runtime personality based on interaction history.
        This does NOT mutate brain.json, only runtime behavior.
        """
        interactions = max(1, self._drift_state["interactions"])
        success_rate = self._drift_state["successes"] / interactions
        frustration_rate = self._drift_state["frustrations"] / interactions

        base = self.identity.get("style", {})

        def clamp(v: float) -> float:
            return max(0.0, min(1.0, v))

        self.personality_runtime["warmth"] = clamp(
            base.get("warmth", 0.72) + (success_rate - frustration_rate) * 0.1
        )
        self.personality_runtime["humor_level"] = clamp(
            base.get("humor_level", 0.35) + (success_rate - frustration_rate) * 0.05
        )
        self.personality_runtime["sarcasm_level"] = clamp(
            base.get("sarcasm_level", 0.18) + (frustration_rate - success_rate) * 0.05
        )
        self.personality_runtime["directness"] = clamp(
            base.get("directness", 0.9) + frustration_rate * 0.05
        )

    def get_personality_runtime(self) -> Dict[str, float]:
        return dict(self.personality_runtime)

    # -------------------------------------------------------------------------
    # Mood engine + decay
    # -------------------------------------------------------------------------

    def get_mood(self) -> Dict[str, float]:
        return dict(self.mood_state)

    def apply_mood_event(self, event: str) -> None:
        """
        Apply a mood modulation event defined in brain.json:
            mood_engine.modulation_rules[event]
        """
        rules = self.mood.get("modulation_rules", {})
        delta = rules.get(event)
        if not delta:
            return

        for key, change in delta.items():
            if not key.endswith("_delta"):
                continue
            mood_key = key.replace("_delta", "")
            current = self.mood_state.get(mood_key, 0.0)
            new_val = max(0.0, min(1.0, current + float(change)))
            self.mood_state[mood_key] = new_val

    def decay_mood(self, factor: float = 0.02, interval: float = 60.0) -> None:
        """
        Gradually move mood back toward baseline over time.
        factor: how strongly to pull toward baseline per decay call.
        interval: minimum seconds between decay applications.
        """
        now = time.time()
        if now - self._last_mood_decay < interval:
            return
        self._last_mood_decay = now

        baseline = self.mood.get("state", {})
        for key, base_val in baseline.items():
            current = self.mood_state.get(key, base_val)
            self.mood_state[key] = current + (base_val - current) * factor

    # -------------------------------------------------------------------------
    # Personality decay
    # -------------------------------------------------------------------------

    def decay_personality(self, factor: float = 0.02, interval: float = 300.0) -> None:
        """
        Gradually move personality_runtime back toward base style over time.
        """
        now = time.time()
        if now - self._last_personality_decay < interval:
            return
        self._last_personality_decay = now

        base = self.identity.get("style", {})
        for key, base_val in base.items():
            if not isinstance(base_val, (int, float)):
                continue
            current = self.personality_runtime.get(key, base_val)
            self.personality_runtime[key] = current + (base_val - current) * factor

    # -------------------------------------------------------------------------
    # Context engine
    # -------------------------------------------------------------------------

    def get_context(self) -> Dict[str, Any]:
        return dict(self.conversation_state)

    def set_current_topic(self, topic: Optional[str]) -> None:
        self.conversation_state["current_topic"] = topic

    def set_current_project(self, project: Optional[str]) -> None:
        self.conversation_state["current_project"] = project

    def set_last_command(self, command_name: Optional[str]) -> None:
        self.conversation_state["last_command"] = command_name

    def add_touched_file(self, path: str) -> None:
        files = self.conversation_state.setdefault("last_files_touched", [])
        if path not in files:
            files.append(path)

    # -------------------------------------------------------------------------
    # Intent engine (scored keyword-based helper)
    # -------------------------------------------------------------------------

    def _score_intent_match(self, user_lower: str, intent: str, words: List[str]) -> float:
        score = 0.0
        for w in words:
            w_lower = w.lower()
            if w_lower in user_lower:
                score += 1.0 + len(w_lower) * 0.01
        if intent == "debugging" and ("error" in user_lower or "traceback" in user_lower):
            score += 0.5
        return score

    def detect_intent(self, user_text: str) -> str:
        """
        Keyword-based intent detection based on brain.json with simple scoring.
        """
        user_lower = user_text.lower()
        detection_cfg = self.intent_cfg.get("detection", {})
        keywords = detection_cfg.get("keywords", {})

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

    # -------------------------------------------------------------------------
    # Command cognition helpers
    # -------------------------------------------------------------------------

    def get_os_specific_commands(self, os_key: str) -> List[str]:
        os_specific = self.command_cfg.get("command_types", {}).get("os_specific", {})
        return os_specific.get(os_key, [])

    def get_cross_platform_commands(self) -> List[str]:
        return self.command_cfg.get("command_types", {}).get("cross_platform", [])

    def should_disambiguate(self, action_type: str) -> bool:
        dis_cfg = self.command_cfg.get("disambiguation", {})
        examples = dis_cfg.get("examples", [])
        return action_type in examples

    # -------------------------------------------------------------------------
    # OS routing helpers
    # -------------------------------------------------------------------------

    def get_os_mapping(self) -> Dict[str, str]:
        return self.os_routing_cfg.get("mapping", {})

    def get_current_os_key(self) -> str:
        sys_name = platform.system().lower()
        mapping = self.get_os_mapping()
        return mapping.get(sys_name, sys_name)

    # -------------------------------------------------------------------------
    # App scanner config
    # -------------------------------------------------------------------------

    def get_app_scanner_config(self) -> Dict[str, Any]:
        return dict(self.app_scanner_cfg)

    # -------------------------------------------------------------------------
    # Reasoning / speaker / listener / safety
    # -------------------------------------------------------------------------

    def get_reasoning_config(self) -> Dict[str, Any]:
        return dict(self.reasoning_cfg)

    def choose_reasoning_mode(self, intent: str) -> str:
        cfg = self.get_reasoning_config()
        mode = cfg.get("mode", "hybrid")
        if mode != "hybrid":
            return mode

        if intent in ("architecture_design", "brain_design", "code_generation"):
            return "llm_reasoner"
        if intent in ("debugging",):
            return "hybrid"
        return "deterministic_reasoner"

    def get_speaker_style(self) -> Dict[str, Any]:
        return self.speaker_cfg.get("style", {})

    def get_speaker_formatting(self) -> Dict[str, Any]:
        return self.speaker_cfg.get("formatting", {})

    def build_speaker_profile(self) -> Dict[str, Any]:
        style = self.get_style()
        mood = self.get_mood()
        personality = self.get_personality_runtime()

        profile = {
            "tone": self.speaker_cfg.get("style", {}).get("default_tone", "direct"),
            "warmth": personality.get("warmth", style.get("warmth", 0.7)),
            "humor_level": personality.get("humor_level", style.get("humor_level", 0.3)),
            "sarcasm_level": personality.get("sarcasm_level", style.get("sarcasm_level", 0.1)),
            "directness": personality.get("directness", style.get("directness", 0.9)),
            "energy": mood.get("energy", 0.5),
            "patience": mood.get("patience", 0.8),
        }
        return profile

    def get_listener_assumptions(self) -> Dict[str, Any]:
        return self.listener_cfg.get("assumptions", {})

    def get_safety_limits(self) -> Dict[str, Any]:
        return self.safety_cfg.get("hard_limits", {})

    def is_action_allowed(self, user_text: str, action_type: str) -> bool:
        limits = self.get_safety_limits()
        text_lower = user_text.lower()

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

    # -------------------------------------------------------------------------
    # Event system
    # -------------------------------------------------------------------------

    def event(self, name: str, *args: Any, **kwargs: Any) -> None:
        """
        High-level event hook to drive mood, context, memory, and drift.
        Examples:
            event("user_confused")
            event("task_success")
            event("topic_change", "architecture")
            event("remember_text", "user_preferences", "I like dark mode")
        """
        name = name.lower()

        if name == "user_confused":
            self.register_interaction(success=False, frustrated_user=True)

        elif name == "task_success":
            self.register_interaction(success=True, frustrated_user=False)

        elif name == "topic_change":
            if args:
                self.set_current_topic(str(args[0]))

        elif name == "remember_text":
            if len(args) >= 2:
                category = str(args[0])
                text = str(args[1])
                self.remember(category, text)

        elif name == "project_change":
            if args:
                self.set_current_project(str(args[0]))

        # You can extend this with more event types as needed.

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    def reload(self) -> None:
        self.load()
        self.load_commands()

    def to_dict(self) -> Dict[str, Any]:
        out = dict(self._config)
        out.setdefault("mood_engine_runtime", {})["state"] = dict(self.mood_state)
        out.setdefault("context_engine_runtime", {})["conversation_state"] = dict(
            self.conversation_state
        )
        out.setdefault("personality_runtime", {}).update(self.personality_runtime)
        out.setdefault("drift_state", {}).update(self._drift_state)
        return out

    # -------------------------------------------------------------------------
    # Debugger helpers
    # -------------------------------------------------------------------------

    def debug_snapshot(self) -> Dict[str, Any]:
        return {
            "identity_name": self.get_display_name(),
            "mood": dict(self.mood_state),
            "personality_runtime": dict(self.personality_runtime),
            "context": dict(self.conversation_state),
            "drift_state": dict(self._drift_state),
            "memory_categories": {
                k: len(v) for k, v in self.memory_store.items()
            },
            "commands_loaded": list(self.commands.keys()),
        }

    def debug_print(self) -> None:
        snap = self.debug_snapshot()
        print("\n=== BRAIN DEBUG SNAPSHOT ===")
        for key, value in snap.items():
            print(f"{key}: {value}")
        print("=== END DEBUG ===\n")

    # -------------------------------------------------------------------------
    # Self-diagnostic
    # -------------------------------------------------------------------------

    def self_test(self) -> Dict[str, Any]:
        report: Dict[str, Any] = {}

        report["identity_loaded"] = bool(self.identity)
        report["drives_loaded"] = bool(self.drives)
        report["mood_engine_loaded"] = bool(self.mood)
        report["memory_config_loaded"] = bool(self.memory_cfg)
        report["context_engine_loaded"] = bool(self.context)
        report["intent_engine_loaded"] = bool(self.intent_cfg)
        report["command_cognition_loaded"] = bool(self.command_cfg)
        report["os_routing_loaded"] = bool(self.os_routing_cfg)
        report["app_scanner_loaded"] = bool(self.app_scanner_cfg)
        report["reasoning_loaded"] = bool(self.reasoning_cfg)
        report["speaker_loaded"] = bool(self.speaker_cfg)
        report["listener_loaded"] = bool(self.listener_cfg)
        report["safety_loaded"] = bool(self.safety_cfg)

        report["mood_runtime_state"] = dict(self.mood_state)
        report["context_runtime_state"] = dict(self.conversation_state)
        report["personality_runtime"] = dict(self.personality_runtime)
        report["drift_state"] = dict(self._drift_state)
        report["memory_category_counts"] = {
            k: len(v) for k, v in self.memory_store.items()
        }
        report["commands_loaded"] = list(self.commands.keys())
        report["aliases_registered"] = list(self.alias_map.keys())

        return report


# Convenience singleton-style accessor
_global_brain: Optional[Brain] = None


def get_brain(config_path: str = "config/brain.json") -> Brain:
    global _global_brain
    if _global_brain is None:
        _global_brain = Brain(config_path=config_path)
    return _global_brain
