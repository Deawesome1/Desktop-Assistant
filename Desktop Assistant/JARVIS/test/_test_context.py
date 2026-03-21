"""
test/test_context.py — Context engine scenario test suite.

Tests confidence scoring, disambiguation threshold, app-based routing boosts,
and time-of-day behavior — all without launching real apps or waiting for real time.

Usage:
    python test/test_context.py
    python test/test_context.py --verbose
"""

import sys
import os
import json
import argparse
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.context import ctx
import bot.command_hub as command_hub

# ── ANSI ──────────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def _ansi():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

# ── Confidence helper (bypasses speaking) ─────────────────────────────────────

def _get_confidence(query: str) -> tuple[str | None, float]:
    """Return (matched_command_key, confidence) for a query."""
    import importlib
    registry_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "commands.json")
    with open(registry_path) as f:
        registry = json.load(f)
    key, _, confidence = command_hub._match_command(query, registry)
    return key, confidence


# ── Scenario definition ────────────────────────────────────────────────────────

class Scenario:
    def __init__(self, name: str, description: str,
                 simulate_hour: int | None = None,
                 simulate_apps: list[str] | None = None,
                 recent_commands: list[str] | None = None):
        self.name            = name
        self.description     = description
        self.simulate_hour   = simulate_hour
        self.simulate_apps   = simulate_apps or []
        self.recent_commands = recent_commands or []

    def setup(self):
        ctx.clear_simulation()
        ctx._command_history.clear()
        ctx._last_suggestion_ts = 0
        if self.simulate_hour is not None:
            ctx.simulate_time(self.simulate_hour)
        if self.simulate_apps:
            ctx.simulate_apps(self.simulate_apps)
        for key in self.recent_commands:
            ctx.record_command(key, f"test {key}")

    def teardown(self):
        ctx.clear_simulation()
        ctx._command_history.clear()


class ConfidenceTest:
    """Assert a query routes to an expected command with expected confidence range."""
    def __init__(self, query: str, expected_command: str,
                 min_confidence: float, max_confidence: float = 1.0,
                 label: str = ""):
        self.query            = query
        self.expected_command = expected_command
        self.min_confidence   = min_confidence
        self.max_confidence   = max_confidence
        self.label            = label or query

    def run(self) -> tuple[bool, str, str, float, float]:
        """Returns (passed, matched_key, expected_key, actual_conf, expected_min)."""
        matched_key, actual_conf = _get_confidence(self.query)
        passed = (
            matched_key == self.expected_command and
            self.min_confidence <= actual_conf <= self.max_confidence
        )
        return passed, matched_key or "NONE", self.expected_command, actual_conf, self.min_confidence


class SuggestionTest:
    """Assert ctx.get_suggestion() returns something (or nothing)."""
    def __init__(self, label: str, expect_suggestion: bool):
        self.label             = label
        self.expect_suggestion = expect_suggestion

    def run(self) -> tuple[bool, str | None]:
        suggestion = ctx.get_suggestion()
        passed = bool(suggestion) == self.expect_suggestion
        return passed, suggestion


# ── Scenario definitions ──────────────────────────────────────────────────────

SCENARIOS = [

    # ── Time: Morning ─────────────────────────────────────────────────────────
    {
        "scenario": Scenario(
            name="Morning (6am)",
            description="news + weather should be boosted at 6am",
            simulate_hour=6,
        ),
        "tests": [
            ConfidenceTest("what's the weather", "weather",     min_confidence=0.75, label="weather boosted at morning"),
            ConfidenceTest("what's in the news",  "news",       min_confidence=0.75, label="news boosted at morning"),
            ConfidenceTest("set a timer for 5 minutes", "timer", min_confidence=0.65, label="timer normal at morning"),
        ],
    },

    # ── Time: Evening ─────────────────────────────────────────────────────────
    {
        "scenario": Scenario(
            name="Evening (8pm)",
            description="reminder + note should be boosted at 8pm",
            simulate_hour=20,
        ),
        "tests": [
            ConfidenceTest("remind me to call mom",    "reminder", min_confidence=0.75, label="reminder boosted at evening"),
            ConfidenceTest("take a note pick up milk", "note",     min_confidence=0.75, label="note boosted at evening"),
            ConfidenceTest("what's the weather",       "weather",  min_confidence=0.50, label="weather normal at evening"),
        ],
    },

    # ── App: Gaming (Steam) ───────────────────────────────────────────────────
    {
        "scenario": Scenario(
            name="Gaming (Steam open)",
            description="open_app should be boosted when Steam is running",
            simulate_apps=["steam.exe"],
        ),
        "tests": [
            ConfidenceTest("open rocket league",   "open_app", min_confidence=0.70, label="open_app boosted (Steam open)"),
            ConfidenceTest("launch game",          "open_app", min_confidence=0.50, label="launch game with Steam open"),
        ],
    },

    # ── App: Homework (Edge) ──────────────────────────────────────────────────
    {
        "scenario": Scenario(
            name="Homework (Edge open)",
            description="wikipedia + calculator boosted when Edge is running",
            simulate_apps=["msedge.exe"],
        ),
        "tests": [
            ConfidenceTest("who is albert einstein",   "wikipedia",  min_confidence=0.70, label="wikipedia boosted (Edge open)"),
            ConfidenceTest("calculate 42 times 7",     "calculator", min_confidence=0.70, label="calculator boosted (Edge open)"),
            ConfidenceTest("define photosynthesis",    "dictionary", min_confidence=0.50, label="dictionary normal (Edge open)"),
        ],
    },

    # ── App: Coding (VS Code) ─────────────────────────────────────────────────
    {
        "scenario": Scenario(
            name="Coding (VS Code open)",
            description="open_browser + wikipedia boosted when Code is running",
            simulate_apps=["code.exe"],
        ),
        "tests": [
            ConfidenceTest("search for python docs",   "open_browser", min_confidence=0.70, label="open_browser boosted (Code open)"),
            ConfidenceTest("tell me about decorators", "wikipedia",    min_confidence=0.70, label="wikipedia boosted (Code open)"),
        ],
    },

    # ── App: Music (Spotify) ──────────────────────────────────────────────────
    {
        "scenario": Scenario(
            name="Music (Spotify open)",
            description="media_control + volume boosted when Spotify is running",
            simulate_apps=["spotify.exe"],
        ),
        "tests": [
            ConfidenceTest("next song",   "media_control", min_confidence=0.70, label="media_control boosted (Spotify open)"),
            ConfidenceTest("volume up",   "volume",        min_confidence=0.70, label="volume boosted (Spotify open)"),
        ],
    },

    # ── Disambiguation: No context ────────────────────────────────────────────
    {
        "scenario": Scenario(
            name="Ambiguous — no context",
            description="Vague queries with no INTENT_CONTEXT word score below 0.55",
        ),
        "tests": [
            # "mute" short trigger, base 0.50 — below threshold
            ConfidenceTest("mute",   "volume",       min_confidence=0.0, max_confidence=0.54,
                           label="'mute' scores 0.50 without context"),
            # "open" matches open_app but is a single short word — base 0.50
            ConfidenceTest("open",   "open_app",     min_confidence=0.0, max_confidence=0.54,
                           label="'open' scores 0.50 without context"),
            # "launch" same — short trigger, base 0.50
            ConfidenceTest("launch", "open_app",     min_confidence=0.0, max_confidence=0.54,
                           label="'launch' scores 0.50 without context"),
        ],
    },

    # ── Disambiguation: With context ──────────────────────────────────────────
    {
        "scenario": Scenario(
            name="Ambiguous — with context",
            description="Same queries should score ABOVE threshold when context is set",
            simulate_apps=["spotify.exe"],
            recent_commands=["volume", "media_control"],
        ),
        "tests": [
            ConfidenceTest("mute",  "volume",        min_confidence=0.55,
                           label="'mute' confident with Spotify + recent volume"),
            ConfidenceTest("play music",  "media_control", min_confidence=0.55,
                           label="'play music' confident with Spotify open"),
        ],
    },

    # ── Suggestion: Morning suggestion fires ──────────────────────────────────
    {
        "scenario": Scenario(
            name="Suggestion — morning, news not run yet",
            description="get_suggestion() should return something at 6am if news not recently run",
            simulate_hour=6,
        ),
        "tests": [
            SuggestionTest("morning suggestion fires", expect_suggestion=True),
            # True once weather/news have been run 3+ times (which happens after a few test runs).
            # On a completely fresh install with 0 runs this would be False.
        ],
    },

    # ── Suggestion: App-based suggestion ─────────────────────────────────────
    {
        "scenario": Scenario(
            name="Suggestion — Steam open",
            description="get_suggestion() should return Steam suggestion when Steam is open",
            simulate_apps=["steam.exe"],
        ),
        "tests": [
            SuggestionTest("Steam suggestion fires", expect_suggestion=True),
        ],
    },

]


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all(verbose: bool = False):
    _ansi()
    total = passed_count = failed_count = 0
    results = []

    print(f"\n{BOLD}  JARVIS Context Scenario Tests{RESET}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    for block in SCENARIOS:
        scenario: Scenario = block["scenario"]
        tests = block["tests"]

        print(f"  {CYAN}{BOLD}{scenario.name}{RESET}")
        print(f"  {DIM}{scenario.description}{RESET}")

        scenario.setup()

        for test in tests:
            total += 1

            if isinstance(test, ConfidenceTest):
                passed, matched, expected, actual_conf, min_conf = test.run()
                if passed:
                    passed_count += 1
                    marker = f"{GREEN}PASS{RESET}"
                else:
                    failed_count += 1
                    marker = f"{RED}FAIL{RESET}"

                conf_bar = "█" * int(actual_conf * 20)
                conf_bar = f"{GREEN}{conf_bar}{RESET}" if actual_conf >= min_conf else f"{RED}{conf_bar}{RESET}"
                conf_bar = f"[{conf_bar:<20}] {actual_conf:.2f}"

                match_str = f"{GREEN}{matched}{RESET}" if matched == expected else f"{RED}{matched}{RESET} (want {expected})"

                print(f"    {marker}  {DIM}{test.label:<45}{RESET}")
                print(f"         routed→ {match_str}   conf {conf_bar}   min {min_conf:.2f}")

                results.append({
                    "scenario": scenario.name, "type": "confidence",
                    "label": test.label, "query": test.query,
                    "matched": matched, "expected": expected,
                    "confidence": round(actual_conf, 3),
                    "min_confidence": min_conf, "passed": passed,
                })

            elif isinstance(test, SuggestionTest):
                passed, suggestion = test.run()
                if passed:
                    passed_count += 1
                    marker = f"{GREEN}PASS{RESET}"
                else:
                    failed_count += 1
                    marker = f"{RED}FAIL{RESET}"

                expected_str = "suggestion" if test.expect_suggestion else "no suggestion"
                got_str = f'"{suggestion[:50]}"' if suggestion else "None"
                print(f"    {marker}  {DIM}{test.label:<45}{RESET}")
                print(f"         expected {expected_str}, got {got_str}")

                results.append({
                    "scenario": scenario.name, "type": "suggestion",
                    "label": test.label, "suggestion": suggestion,
                    "expected_suggestion": test.expect_suggestion, "passed": passed,
                })

        scenario.teardown()

        group_pass = sum(1 for r in results[-len(tests):] if r["passed"])
        color = GREEN if group_pass == len(tests) else (YELLOW if group_pass > 0 else RED)
        print(f"    {color}  {group_pass}/{len(tests)} passed{RESET}\n")

    # ── Summary ───────────────────────────────────────────────────────────────
    pct = int(passed_count / total * 100) if total else 0
    bar = f"{GREEN}{'█' * int(40 * passed_count / total)}{RESET}{DIM}{'░' * (40 - int(40 * passed_count / total))}{RESET}" if total else ""

    print(f"  {BOLD}Results: {passed_count}/{total} passed  ({pct}%){RESET}")
    print(f"  [{bar}]")

    failed = [r for r in results if not r["passed"]]
    if failed:
        print(f"\n  {RED}{BOLD}Failed:{RESET}")
        for r in failed:
            print(f"    {RED}✗{RESET}  [{r['scenario']}]  {r['label']}")

    # Save report
    report_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(report_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(report_dir, f"context_report_{ts}.json")
    with open(path, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(),
                   "total": total, "passed": passed_count,
                   "failed": failed_count, "results": results}, f, indent=2)
    print(f"\n  {DIM}Report saved: {path}{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    run_all(verbose=args.verbose)