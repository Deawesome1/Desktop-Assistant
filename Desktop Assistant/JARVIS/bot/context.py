"""
bot/context.py — JARVIS context engine.

Two-layer context system:
  Memory layer  — fast in-process state (command history, open apps, session time)
  Pattern layer — persisted JSON (app associations, time patterns, command frequency)

Other modules import from here:
  from bot.context import ctx
  ctx.record_command(key, query)
  ctx.get_open_apps()
  ctx.get_confidence_boost(command_key)
  ctx.get_suggestion()
  ctx.get_time_mode()
"""

import os
import sys
import json
import time
import threading
import datetime
from collections import deque

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT           = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATTERNS_PATH   = os.path.join(_ROOT, "config", "context_patterns.json")

# ── Default patterns (written on first run if missing) ────────────────────────
DEFAULT_PATTERNS = {
    "app_associations": {
        "msedge.exe":       {"label": "homework",  "suggestion": "I see Edge is open — need help with homework?",   "boost_commands": ["wikipedia", "calculator", "dictionary"]},
        "chrome.exe":       {"label": "browsing",  "suggestion": None,                                               "boost_commands": ["open_browser", "youtube", "news"]},
        "steam.exe":        {"label": "gaming",    "suggestion": "Steam is open — want to launch a game?",          "boost_commands": ["open_app"]},
        "discord.exe":      {"label": "social",    "suggestion": None,                                               "boost_commands": []},
        "spotify.exe":      {"label": "music",     "suggestion": None,                                               "boost_commands": ["media_control", "volume"]},
        "vlc.exe":          {"label": "media",     "suggestion": None,                                               "boost_commands": ["media_control", "volume"]},
        "code.exe":         {"label": "coding",    "suggestion": "VS Code is open — need anything looked up?",      "boost_commands": ["wikipedia", "open_browser"]},
        "pycharm64.exe":    {"label": "coding",    "suggestion": None,                                               "boost_commands": ["wikipedia", "open_browser"]},
        "obs64.exe":        {"label": "streaming", "suggestion": "OBS is open — recording or streaming?",           "boost_commands": ["media_control", "volume"]},
        "excel.exe":        {"label": "work",      "suggestion": None,                                               "boost_commands": ["calculator", "note"]},
        "winword.exe":      {"label": "writing",   "suggestion": None,                                               "boost_commands": ["dictionary", "note"]},
    },
    "time_patterns": {
        "morning":    {"hours": [6, 7, 8, 9],        "typical_commands": ["weather", "news", "greet"],    "greeting": "Good morning."},
        "midday":     {"hours": [10, 11, 12, 13],    "typical_commands": [],                               "greeting": None},
        "afternoon":  {"hours": [14, 15, 16, 17],    "typical_commands": [],                               "greeting": None},
        "evening":    {"hours": [18, 19, 20, 21],    "typical_commands": ["reminder", "note", "weather"], "greeting": None},
        "night":      {"hours": [22, 23],            "typical_commands": ["reminder", "timer"],            "greeting": None},
        "late_night": {"hours": [0, 1, 2, 3, 4, 5], "typical_commands": ["timer"],                        "greeting": None},
    },
    "command_frequency":   {},
    "suggestion_cooldown": 300,
    "disambiguation_threshold": 0.55,
    "disambiguation_timeout":   6,
}


# ── Context class ─────────────────────────────────────────────────────────────
class ContextEngine:
    def __init__(self):
        self._lock              = threading.Lock()
        self._command_history   = deque(maxlen=10)   # (key, query, ts)
        self._open_apps         = set()
        self._session_start     = datetime.datetime.now()
        self._patterns          = self._load_patterns()
        self._last_suggestion_ts = 0
        self._app_watcher_running = False
        self._simulated_hour: int | None = None
        self._simulated_apps: bool = False

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_patterns(self) -> dict:
        if os.path.exists(PATTERNS_PATH):
            try:
                with open(PATTERNS_PATH) as f:
                    data = json.load(f)
                # Merge defaults for any missing keys
                for k, v in DEFAULT_PATTERNS.items():
                    if k not in data:
                        data[k] = v
                return data
            except Exception:
                pass
        self._save_patterns(DEFAULT_PATTERNS)
        return dict(DEFAULT_PATTERNS)

    def _save_patterns(self, data: dict = None):
        try:
            os.makedirs(os.path.dirname(PATTERNS_PATH), exist_ok=True)
            with open(PATTERNS_PATH, "w") as f:
                json.dump(data or self._patterns, f, indent=2)
        except Exception:
            pass

    # ── Command recording ─────────────────────────────────────────────────────

    def record_command(self, command_key: str, query: str):
        """Call after every successful command dispatch."""
        ts = time.time()
        with self._lock:
            self._command_history.append((command_key, query, ts))
            freq = self._patterns.setdefault("command_frequency", {})
            freq[command_key] = freq.get(command_key, 0) + 1

        # Persist frequency update (debounced — every 10 commands)
        total = sum(self._patterns["command_frequency"].values())
        if total % 10 == 0:
            self._save_patterns()

    def recent_commands(self, n: int = 5) -> list[str]:
        """Return last n command keys."""
        with self._lock:
            return [c[0] for c in list(self._command_history)[-n:]]

    # ── App watcher ───────────────────────────────────────────────────────────

    def start_app_watcher(self):
        """Start background thread that polls open processes every 30s."""
        if self._app_watcher_running:
            return
        self._app_watcher_running = True
        t = threading.Thread(target=self._watch_apps, daemon=True)
        t.start()

    def _watch_apps(self):
        while True:
            try:
                import psutil
                names = {p.name().lower() for p in psutil.process_iter(["name"])}
                with self._lock:
                    self._open_apps = names
            except Exception:
                pass
            time.sleep(30)

    def get_open_apps(self) -> set:
        with self._lock:
            return set(self._open_apps)

    def get_matched_app_associations(self) -> list[dict]:
        """Return app_association entries for currently open apps."""
        open_apps = self.get_open_apps()
        matched = []
        for proc, info in self._patterns.get("app_associations", {}).items():
            if proc in open_apps:
                matched.append({**info, "process": proc})
        return matched

    # ── Time mode ─────────────────────────────────────────────────────────────

    def get_time_mode(self) -> str:
        """Return current time period. Respects simulate_time() override."""
        hour = self._simulated_hour if self._simulated_hour is not None                else datetime.datetime.now().hour
        for mode, data in self._patterns.get("time_patterns", {}).items():
            if hour in data.get("hours", []):
                return mode
        return "midday"

    def get_time_greeting(self) -> str | None:
        mode = self.get_time_mode()
        return self._patterns.get("time_patterns", {}).get(mode, {}).get("greeting")

    def get_typical_commands_now(self) -> list[str]:
        mode = self.get_time_mode()
        return self._patterns.get("time_patterns", {}).get(mode, {}).get("typical_commands", [])

    # ── Confidence boost ──────────────────────────────────────────────────────

    def get_confidence_boost(self, command_key: str) -> float:
        """
        Return a confidence boost (0.0 – 0.35) for a candidate command
        based on current context:
          +0.20 if an open app boosts this command
          +0.15 if it appears in recent command history
          +0.10 if it's typical for this time of day
        """
        boost = 0.0

        # App boost
        for assoc in self.get_matched_app_associations():
            if command_key in assoc.get("boost_commands", []):
                boost += 0.20
                break

        # Recent command boost
        if command_key in self.recent_commands(5):
            boost += 0.15

        # Time-of-day boost
        if command_key in self.get_typical_commands_now():
            boost += 0.10

        return min(boost, 0.35)

    # ── Proactive suggestions ─────────────────────────────────────────────────

    def get_suggestion(self) -> str | None:
        """
        Return a proactive suggestion string if one is appropriate,
        or None if cooldown hasn't elapsed or nothing relevant.
        """
        cooldown = self._patterns.get("suggestion_cooldown", 300)
        if time.time() - self._last_suggestion_ts < cooldown:
            return None

        # App-based suggestions
        for assoc in self.get_matched_app_associations():
            suggestion = assoc.get("suggestion")
            if suggestion:
                self._last_suggestion_ts = time.time()
                return suggestion

        # Time-based suggestions
        typical = self.get_typical_commands_now()
        recent  = self.recent_commands(5)
        for cmd in typical:
            if cmd not in recent:
                freq = self._patterns.get("command_frequency", {}).get(cmd, 0)
                if freq >= 3:
                    self._last_suggestion_ts = time.time()
                    return f"You usually run {cmd.replace('_', ' ')} around this time."

        return None

    # ── Settings ──────────────────────────────────────────────────────────────

    @property
    def disambiguation_threshold(self) -> float:
        return self._patterns.get("disambiguation_threshold", 0.55)

    @property
    def disambiguation_timeout(self) -> int:
        return self._patterns.get("disambiguation_timeout", 6)

    def add_app_association(self, process: str, label: str,
                            suggestion: str | None, boost_commands: list[str]):
        """Programmatically add or update an app association."""
        self._patterns.setdefault("app_associations", {})[process] = {
            "label":          label,
            "suggestion":     suggestion,
            "boost_commands": boost_commands,
        }
        self._save_patterns()


    # ── Test / simulation hooks ───────────────────────────────────────────────

    def simulate_apps(self, process_names: list[str]):
        """Inject fake open processes for testing. Overrides real app poll."""
        with self._lock:
            self._open_apps = {p.lower() for p in process_names}
            self._simulated_apps = True

    def simulate_time(self, hour: int):
        """Override the current hour for time-mode testing (0-23)."""
        self._simulated_hour = hour

    def clear_simulation(self):
        """Remove all simulation overrides."""
        with self._lock:
            self._open_apps = set()
            self._simulated_apps = False
        self._simulated_hour = None

    def get_time_mode(self) -> str:
        hour = self._simulated_hour if self._simulated_hour is not None                else datetime.datetime.now().hour
        for mode, data in self._patterns.get("time_patterns", {}).items():
            if hour in data.get("hours", []):
                return mode
        return "midday"


# ── Singleton ─────────────────────────────────────────────────────────────────
ctx = ContextEngine()