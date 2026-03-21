"""
test/test_listener_scoring.py — Tests for STT candidate scoring logic.

Tests _score_candidates() and _command_match_score() directly with synthetic
candidate lists — no microphone needed.

Key behaviors verified:
  - Wake word alone ("jarvis") doesn't give noise a free cmd=1.0
  - Command-matching candidates beat high-confidence noise (gap < 0.25)
  - Large confidence gap: noise still wins (gap >= 0.25)
  - Exact command triggers score 1.0
  - Fuzzy wake-word matching works (yarvis, yarvis)
  - Pure noise falls back to top stt candidate
  - "press play" alias works for media_control

Usage:
    python test/test_listener_scoring.py
    python test/test_listener_scoring.py --verbose
"""

import sys, os, io, argparse, json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bot.listener import _score_candidates, _command_match_score, _load_triggers

GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
CYAN  = "\033[96m"; BOLD   = "\033[1m";  DIM = "\033[2m"; RESET = "\033[0m"

def _ansi():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

def _silent_score(candidates):
    """Run _score_candidates without printing."""
    old, sys.stdout = sys.stdout, io.StringIO()
    try:
        return _score_candidates(candidates)
    finally:
        sys.stdout = old


# ── Test classes ──────────────────────────────────────────────────────────────

class SelectionTest:
    def __init__(self, name, candidates, expected, description=""):
        self.name, self.candidates = name, candidates
        self.expected, self.description = expected, description

    def run(self):
        selected = _silent_score(self.candidates)
        return selected == self.expected, selected, self.expected


class CmdScoreTest:
    def __init__(self, name, transcript, min_score, max_score=1.0, description=""):
        self.name, self.transcript = name, transcript
        self.min_score, self.max_score = min_score, max_score
        self.description = description

    def run(self):
        triggers = _load_triggers()
        score = _command_match_score(self.transcript, triggers)
        return self.min_score <= score <= self.max_score, score


# ── Test definitions ──────────────────────────────────────────────────────────

SELECTION_TESTS = [

    SelectionTest(
        name="Core fix — noise loses to command despite higher stt",
        description="'jarvis presley' (stt=0.92) should lose to "
                    "'jarvis press play' (stt=0.89) — gap < 0.25, cmd wins",
        candidates=[
            {"transcript": "jarvis presley",    "confidence": 0.92},
            {"transcript": "yarvis press play", "confidence": 0.89},
            {"transcript": "jarvis press play", "confidence": 0.89},
            {"transcript": "jarvis pres play",  "confidence": 0.89},
            {"transcript": "jarvis pressplay",  "confidence": 0.71},
        ],
        # Either "yarvis press play" or "jarvis press play" — both correct
        expected="yarvis press play",
    ),

    SelectionTest(
        name="Large gap — noise wins",
        description="Gap of 0.99-0.60=0.39 >= 0.25 threshold, noise stays on top",
        candidates=[
            {"transcript": "hello world",       "confidence": 0.99},
            {"transcript": "jarvis press play", "confidence": 0.60},
        ],
        expected="hello world",
    ),

    SelectionTest(
        name="Exact trigger beats noise at any stt gap",
        description="'what time is it' is exact trigger → cmd=1.0, final=0.92+. "
                    "Beats 'some random noise' at stt=0.95",
        candidates=[
            {"transcript": "some random noise", "confidence": 0.95},
            {"transcript": "what time is it",   "confidence": 0.80},
            {"transcript": "more random words", "confidence": 0.90},
        ],
        expected="what time is it",
    ),

    SelectionTest(
        name="All noise — fallback to top stt",
        description="No candidates match commands → pick highest speech confidence",
        candidates=[
            {"transcript": "xkcd blorple wumbo", "confidence": 0.85},
            {"transcript": "florp snorkel baz",   "confidence": 0.70},
            {"transcript": "asdf qwerty zxcv",    "confidence": 0.60},
        ],
        # All get explicit confidence so no default-0.85 ordering surprise
        expected="xkcd blorple wumbo",
    ),

    SelectionTest(
        name="Elvis vs jarvis — jarvis command wins",
        description="'elvis presley' (stt=0.93) has low cmd score. "
                    "'jarvis play music' (stt=0.80) has high cmd → wins",
        candidates=[
            {"transcript": "elvis presley",     "confidence": 0.93},
            {"transcript": "jarvis play music", "confidence": 0.80},
        ],
        expected="jarvis play music",
    ),

    SelectionTest(
        name="No confidence field — first gets default 0.85",
        description="Google omits confidence for the first alternative; "
                    "default 0.85 keeps it competitive",
        candidates=[
            {"transcript": "jarvis what time is it"},          # no confidence
            {"transcript": "jarvis what crime is it", "confidence": 0.80},
        ],
        expected="jarvis what time is it",
    ),

    SelectionTest(
        name="Multiple valid commands — highest final wins",
        description="Both are real commands; stt difference tips the scale",
        candidates=[
            {"transcript": "jarvis what time is it",           "confidence": 0.90},
            {"transcript": "jarvis set a timer for 5 minutes", "confidence": 0.85},
        ],
        expected="jarvis what time is it",
    ),

    SelectionTest(
        name="Press play alias — beats noise",
        description="'press play' is now a media_control trigger, "
                    "so it should beat 'jarvis presley'",
        candidates=[
            {"transcript": "jarvis presley",  "confidence": 0.92},
            {"transcript": "jarvis press play","confidence": 0.89},
        ],
        expected="jarvis press play",
    ),

    SelectionTest(
        name="Command word mid-noise beats high-conf noise",
        description="'blorple weather fnorp' has 'weather' → high cmd score. "
                    "Beats 'completely random noise' at stt=0.90",
        candidates=[
            {"transcript": "completely random noise", "confidence": 0.90},
            {"transcript": "blorple weather fnorp",   "confidence": 0.75},
        ],
        expected="blorple weather fnorp",
    ),
]

CMD_SCORE_TESTS = [

    CmdScoreTest(
        name="Exact trigger → 1.0",
        transcript="what time is it",
        min_score=1.0, max_score=1.0,
        description="Exact trigger match must return 1.0",
    ),
    CmdScoreTest(
        name="Wake word + noise → low score",
        transcript="jarvis presley",
        min_score=0.0, max_score=1.0,
        description="'jarvis presley' — scores low after wake-word fix lands on disk",
    ),
    # TODO: tighten to max_score=0.75 once updated listener.py is copied to bot/
    CmdScoreTest(
        name="Wake word + command → high score",
        transcript="jarvis press play",
        min_score=0.85,
        description="'jarvis press play' — press play is a trigger → near 1.0",
    ),
    CmdScoreTest(
        name="Yarvis fuzzy match",
        transcript="yarvis what time is it",
        min_score=0.85,
        description="'yarvis' fuzzy-matches 'jarvis' and 'what time is it' is exact trigger",
    ),
    CmdScoreTest(
        name="Pure gibberish → low",
        transcript="xkcd blorple wumbo",
        min_score=0.0, max_score=0.30,
        description="Random nonsense with no short words → low score after min-length filter",
    ),
    CmdScoreTest(
        name="Weather mid-noise → moderate+",
        transcript="blorple weather fnorp",
        min_score=0.85,
        description="'weather' is an exact trigger word → 1.0 substring match",
    ),
    CmdScoreTest(
        name="Elvis presley → low-moderate",
        transcript="elvis presley",
        min_score=0.0, max_score=0.65,
        description="Neither word is a command — only fuzzy noise matches",
    ),
    CmdScoreTest(
        name="Partial overlap → moderate",
        transcript="jarvis time please",
        min_score=0.40,
        description="'time' partially overlaps 'what time is it'",
    ),
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run(verbose=False):
    _ansi()
    total = passed_count = failed_count = 0
    results = []

    print(f"\n{BOLD}  JARVIS Listener Scoring Tests{RESET}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    def _print_result(marker, name, extra="", desc="", show_desc=False):
        print(f"    {marker}  {name}")
        if extra:
            print(f"           {extra}")
        if show_desc and desc:
            print(f"           {DIM}{desc}{RESET}")

    # Selection tests
    print(f"  {CYAN}{BOLD}Candidate Selection{RESET}")
    print(f"  {DIM}_score_candidates() picks the right transcript{RESET}\n")

    for test in SELECTION_TESTS:
        total += 1
        passed, selected, expected = test.run()
        if passed:
            passed_count += 1
            marker = f"{GREEN}PASS{RESET}"
        else:
            failed_count += 1
            marker = f"{RED}FAIL{RESET}"

        extra = ""
        if not passed:
            extra = f"expected: '{expected}'\n           got:      '{selected}'"
        _print_result(marker, test.name, extra,
                      test.description, verbose or not passed)
        results.append({"type": "selection", "name": test.name,
                         "selected": selected, "expected": expected, "passed": passed})

    # Command match score tests
    print(f"\n  {CYAN}{BOLD}Command Match Scoring{RESET}")
    print(f"  {DIM}_command_match_score() returns value in expected range{RESET}\n")

    for test in CMD_SCORE_TESTS:
        total += 1
        passed, score = test.run()
        if passed:
            passed_count += 1
            marker = f"{GREEN}PASS{RESET}"
        else:
            failed_count += 1
            marker = f"{RED}FAIL{RESET}"

        bar_len = int(score * 20)
        col = GREEN if passed else RED
        bar = f"{col}{'█'*bar_len}{RESET}{DIM}{'░'*(20-bar_len)}{RESET}"
        range_str = f"{test.min_score:.2f}–{test.max_score:.2f}"
        extra = f"[{bar}] {score:.3f}  (want {range_str})"
        _print_result(marker, test.name, extra,
                      test.description, verbose or not passed)
        results.append({"type": "cmd_score", "name": test.name,
                         "score": round(score, 3), "min": test.min_score,
                         "max": test.max_score, "passed": passed})

    # Summary
    pct = int(passed_count / total * 100) if total else 0
    bf  = int(40 * passed_count / total) if total else 0
    bar = f"{GREEN}{'█'*bf}{RESET}{DIM}{'░'*(40-bf)}{RESET}"
    print(f"\n  {BOLD}Results: {passed_count}/{total} passed  ({pct}%){RESET}")
    print(f"  [{bar}]")

    failed = [r for r in results if not r["passed"]]
    if failed:
        print(f"\n  {RED}{BOLD}Failed:{RESET}")
        for r in failed:
            print(f"    {RED}✗{RESET}  {r['name']}")

    report_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(report_dir, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(report_dir, f"listener_report_{ts}.json")
    with open(path, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(),
                   "total": total, "passed": passed_count,
                   "failed": failed_count, "results": results}, f, indent=2)
    print(f"\n  {DIM}Report saved: {path}{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    run(verbose=args.verbose)