"""
test/test_all_commands.py — JARVIS command test runner.

Modes:
  Manual (default): pauses after each result so you can hear/read it.
  Auto:             runs all tests unattended and saves a report.

Usage:
  python test/test_all_commands.py           # manual mode
  python test/test_all_commands.py --auto    # auto mode (saves report)
  python test/test_all_commands.py --auto --groups time_date,calculator
"""

import sys
import os
import time
import json
import argparse
from datetime import datetime

_JARVIS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _JARVIS_ROOT)
import bot.command_hub as command_hub

# ── Silence JARVIS during tests ───────────────────────────────────────────────
# Automatically mutes on start, restores original state when done.
try:
    import json as _json
    _voice_config = os.path.join(os.path.dirname(__file__), "..", "config", "voice.json")
    _voice_data   = _json.load(open(_voice_config))
    _was_muted    = _voice_data.get("mute", False)
    _voice_data["mute"] = True
    _json.dump(_voice_data, open(_voice_config, "w"), indent=2)
except Exception as _e:
    _was_muted = False
    print(f"[Test] Could not mute voice: {_e}")

import atexit as _atexit

def _restore_voice():
    try:
        import json as _j
        _cfg  = os.path.join(os.path.dirname(__file__), "..", "config", "voice.json")
        _data = _j.load(open(_cfg))
        _data["mute"] = _was_muted
        _j.dump(_data, open(_cfg, "w"), indent=2)
    except Exception:
        pass

_atexit.register(_restore_voice)

# ── Toggle which groups to run ────────────────────────────────────────────────
RUN = {
    "time_date":         True,
    "greet":             True,
    "calculator":        True,
    "weather":           True,
    "timer":             True,
    "stopwatch":         True,
    "reminder":          False,   # fires async at real time — skip in auto
    "volume":            True,
    "brightness":        True,
    "screenshot":        True,
    "clipboard":         True,
    "clipboard_history": True,
    "note":              True,
    "system_info":       True,
    "top_processes":     True,
    "wifi_info":         True,
    "ip_address":        True,
    "open_browser":      True,
    "youtube":           True,
    "open_app":          False,   # actually launches apps
    "recycle_bin":       False,   # actually empties trash
    "shutdown":          False,   # actually shuts down
    "media_control":     True,
    "news":              True,
    "wikipedia":         True,
    "dictionary":        True,
    "converter":         True,
    "jokes":             True,
    "small_talk":        True,
}

# ── Test cases ────────────────────────────────────────────────────────────────
TESTS = {
    "time_date": [
        "what time is it",
        "what's the date today",
        "what day is it",
    ],
    "greet": [
        "hello jarvis",
        "good morning",
        "good evening",
    ],
    "calculator": [
        "calculate 15 plus 27",
        "calculate 144 divided by 12",
        "square root of 256",
        "20 percent of 350",
        "7 times 8",
        "5 squared",
    ],
    "weather": [
        "what's the weather",
        "weather in New York",
        "temperature in London",
    ],
    "timer": [
        "set a timer for 3 seconds",
        "timer for 1 minute",
        "set a timer for 2 minutes and 30 seconds",
    ],
    "stopwatch": [
        "start stopwatch",
        "stopwatch lap",
        "stop stopwatch",
        "my stopwatch",
        "reset stopwatch",
    ],
    "reminder": [
        "remind me in 1 minute to check the oven",
    ],
    "volume": [
        "volume up",
        "set volume to 50",
        "volume down",
        "mute",
        "unmute",
        "what's the volume",
    ],
    "brightness": [
        "brightness up",
        "set brightness to 70",
        "what's my brightness",
    ],
    "screenshot": [
        "take a screenshot",
        "capture screen",
    ],
    "clipboard": [
        "read clipboard",
        "what's in my clipboard",
        "clear clipboard",
    ],
    "clipboard_history": [
        "clipboard history",
        "last copied",
    ],
    "note": [
        "take a note buy groceries tomorrow",
        "make a note finish the report by Friday",
        "note this call mom on Sunday",
    ],
    "system_info": [
        "system info",
        "how's my pc",
        "cpu usage",
        "ram usage",
        "disk space",
        "uptime",
    ],
    "top_processes": [
        "top processes",
        "using the most cpu",
        "what's using ram",
    ],
    "wifi_info": [
        "wifi",
        "what network am I on",
        "signal strength",
    ],
    "ip_address": [
        "what's my ip address",
        "my local ip",
        "what's my public ip",
    ],
    "open_browser": [
        "open browser",
        "search for python tutorials",
        "google best coffee shops near me",
    ],
    "youtube": [
        "search youtube for lo fi hip hop",
        "youtube",
        "play on youtube dark side of the moon",
    ],
    "open_app": [
        "open notepad",
        "launch calculator",
        "close notepad",
    ],
    "recycle_bin": [
        "empty recycle bin",
    ],
    "shutdown": [
        "lock my pc",
    ],
    "media_control": [
        "pause music",
        "next song",
        "previous song",
        "skip track",
    ],
    "news": [
        "what's in the news",
        "tech news",
        "sports headlines",
        "news about artificial intelligence",
    ],
    "wikipedia": [
        "who is Nikola Tesla",
        "tell me about the Roman Empire",
        "wiki black holes",
    ],
    "dictionary": [
        "define ephemeral",
        "what does lucid mean",
        "definition of serendipity",
        "what is the meaning of cogent",
    ],
    "converter": [
        "convert 5 miles to kilometers",
        "convert 100 fahrenheit to celsius",
        "convert 10 kilograms to pounds",
        "convert 60 mph to meters per second",
        "how many feet in 2 meters",
    ],
    "jokes": [
        "tell me a joke",
        "say something funny",
        "make me laugh",
    ],
    "small_talk": [
        "how are you",
        "what are you",
        "are you real",
        "you're amazing",
        "thanks",
        "good job",
        "shut up",
    ],
}

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def _enable_ansi():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

FAILURE_PREFIXES = ("failed", "error", "couldn't", "not found", "not_found",
                    "disabled", "not installed", "no match", "exception")

FAILURE_EXACT = ("failed", "not_found", "disabled")  # exact full-string matches

def _is_failure(result: str) -> bool:
    r = result.lower().strip()
    if r in FAILURE_EXACT:
        return True
    return any(r.startswith(p) for p in FAILURE_PREFIXES)

def _run_prompt(prompt: str) -> tuple[str, bool, float]:
    """Run a single prompt. Returns (result, passed, elapsed_seconds)."""
    import traceback
    t0 = time.time()
    try:
        result = command_hub.handle(prompt)
        elapsed = time.time() - t0
        passed = not _is_failure(str(result))
        return str(result), passed, elapsed
    except Exception as e:
        elapsed = time.time() - t0
        tb = traceback.format_exc().strip().split("\n")[-1]
        return f"EXCEPTION: {type(e).__name__}: {e} | {tb}", False, elapsed


# ── Manual mode ───────────────────────────────────────────────────────────────

def run_manual(groups: list[str]):
    for group in groups:
        prompts = TESTS.get(group, [])
        print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
        print(f"{BOLD}{CYAN}  {group.upper().replace('_', ' ')}{RESET}")
        print(f"{CYAN}{'─'*60}{RESET}")
        for prompt in prompts:
            print(f"\n  {DIM}> {prompt}{RESET}")
            result, passed, elapsed = _run_prompt(prompt)
            color = GREEN if passed else RED
            print(f"  {color}← {result}{RESET}  {DIM}({elapsed:.2f}s){RESET}")
            input(f"  {DIM}[press Enter for next]{RESET}")
    print(f"\n{BOLD}  Done.{RESET}\n")


# ── Auto mode ─────────────────────────────────────────────────────────────────

def run_auto(groups: list[str]):
    results = []
    total = passed_count = failed_count = 0

    print(f"\n{BOLD}  Running {sum(len(TESTS[g]) for g in groups if g in TESTS)} tests across {len(groups)} groups...{RESET}\n")

    for group in groups:
        prompts = TESTS.get(group, [])
        group_passed = group_failed = 0

        print(f"  {CYAN}{group.upper().replace('_', ' ')}{RESET}")

        for prompt in prompts:
            result, passed, elapsed = _run_prompt(prompt)
            total += 1
            if passed:
                passed_count += 1
                group_passed += 1
                marker = f"{GREEN}PASS{RESET}"
            else:
                failed_count += 1
                group_failed += 1
                marker = f"{RED}FAIL{RESET}"

            print(f"    {marker}  {DIM}{prompt:<45}{RESET}  {result[:60]}")
            results.append({
                "group":   group,
                "prompt":  prompt,
                "result":  result,
                "passed":  passed,
                "elapsed": round(elapsed, 3),
            })

        status = GREEN if group_failed == 0 else (YELLOW if group_passed > 0 else RED)
        print(f"    {status}  {group_passed}/{group_passed + group_failed} passed{RESET}\n")

    # ── Summary ───────────────────────────────────────────────────────────────
    pct = int(passed_count / total * 100) if total else 0
    bar_filled = int(40 * passed_count / total) if total else 0
    bar = f"{GREEN}{'█' * bar_filled}{RESET}{DIM}{'░' * (40 - bar_filled)}{RESET}"

    print(f"\n  {BOLD}Results: {passed_count}/{total} passed  ({pct}%){RESET}")
    print(f"  [{bar}]")

    failed_tests = [r for r in results if not r["passed"]]
    if failed_tests:
        print(f"\n  {RED}{BOLD}Failed:{RESET}")
        for r in failed_tests:
            print(f"    {RED}✗{RESET}  [{r['group']}]  '{r['prompt']}'")
            print(f"       {DIM}{r['result'][:80]}{RESET}")

    # ── Save report ───────────────────────────────────────────────────────────
    report_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(report_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(report_dir, f"test_report_{ts}.json")

    report = {
        "timestamp":    datetime.now().isoformat(),
        "total":        total,
        "passed":       passed_count,
        "failed":       failed_count,
        "pass_rate":    f"{pct}%",
        "groups_run":   groups,
        "results":      results,
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  {DIM}Report saved: {report_path}{RESET}\n")

    # Session stats from logger
    try:
        from logs.logger import print_session_summary
        print_session_summary()
    except Exception:
        pass


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    _enable_ansi()

    parser = argparse.ArgumentParser(description="JARVIS command test runner")
    parser.add_argument("--auto",   action="store_true", help="Run unattended, save report")
    parser.add_argument("--groups", type=str, default="", help="Comma-separated group names to run")
    args = parser.parse_args()

    # Determine which groups to run
    if args.groups:
        groups = [g.strip() for g in args.groups.split(",") if g.strip() in TESTS]
    else:
        groups = [k for k, v in RUN.items() if v and k in TESTS]

    skipped = [k for k, v in RUN.items() if not v]

    print(f"\n{BOLD}  JARVIS Command Test Runner{RESET}")
    print(f"  Mode: {'AUTO' if args.auto else 'MANUAL'}")
    print(f"  {GREEN}Running:{RESET} {', '.join(groups)}")
    if skipped:
        print(f"  {YELLOW}Skipped:{RESET} {', '.join(skipped)}")
    print()

    if args.auto:
        run_auto(groups)
    else:
        input("  Press Enter to begin...\n")
        run_manual(groups)


if __name__ == "__main__":
    main()
# This line intentionally left blank - file was appended to trigger re-download