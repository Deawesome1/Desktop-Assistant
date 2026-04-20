"""
test/test_dj.py — JARVIS DJ system tests.

Tests provider detection, vibe resolution, query parsing, queue management,
time-aware defaults, and pattern learning — no browser or audio needed.

Usage:
    python test/test_dj.py
    python test/test_dj.py --verbose
"""

import sys
import os
import json
import argparse
import importlib
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch webbrowser.open so no browser launches during tests
import webbrowser
_opened_urls = []
webbrowser.open = lambda url, **kw: _opened_urls.append(url) or True

from bot.context import ctx
import commands.dj as dj

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

# ── Silence speak() during tests ─────────────────────────────────────────────
import bot.speaker as _spk
_spk_orig = _spk.speak
_spk.speak = lambda t: None

def _reset():
    """Reset state between tests."""
    _opened_urls.clear()
    dj._queue.clear()
    ctx.clear_simulation()
    ctx._command_history.clear()
    ctx._last_suggestion_ts = 0
    # Reset dj_config to clean state
    cfg = dj._load_cfg()
    cfg["dj_mode"] = False
    cfg["default_provider"] = "youtube_music"
    dj._save_cfg(cfg)


# ── Test class ────────────────────────────────────────────────────────────────

class DJTest:
    def __init__(self, name: str, fn, description: str = ""):
        self.name = name
        self.fn   = fn
        self.description = description

    def run(self) -> tuple[bool, str]:
        _reset()
        try:
            result = self.fn()
            if result is True or result is None:
                return True, ""
            if result is False:
                return False, "assertion returned False"
            return True, ""
        except AssertionError as e:
            return False, str(e)
        except Exception as e:
            import traceback
            return False, f"{type(e).__name__}: {e}\n{traceback.format_exc().strip().split(chr(10))[-1]}"


# ── Test definitions ──────────────────────────────────────────────────────────

def test_default_provider_youtube_music():
    """Default provider should be youtube_music."""
    ctx.simulate_apps([])
    provider = dj._detect_provider()
    assert provider == "youtube_music", f"Expected youtube_music, got {provider}"

def test_spotify_detected_when_open():
    """Spotify app open → provider = spotify."""
    ctx.simulate_apps(["spotify.exe"])
    provider = dj._detect_provider()
    assert provider == "spotify", f"Expected spotify, got {provider}"

def test_browser_open_uses_youtube_music():
    """Opera open → uses default youtube_music (YouTube Music preferred)."""
    ctx.simulate_apps(["opera.exe"])
    provider = dj._detect_provider()
    assert provider == "youtube_music", f"Expected youtube_music, got {provider}"

def test_play_opens_youtube_music_url():
    """'play tame impala' should open YouTube Music search URL."""
    ctx.simulate_apps([])
    dj.run("play tame impala")
    assert _opened_urls, "No URL was opened"
    assert "music.youtube.com" in _opened_urls[-1], \
        f"Expected YouTube Music URL, got: {_opened_urls[-1]}"
    assert "tame+impala" in _opened_urls[-1].lower() or \
           "tame%20impala" in _opened_urls[-1].lower(), \
        f"Query not in URL: {_opened_urls[-1]}"

def test_provider_override_spotify():
    """'play tame impala on spotify' should use Spotify URL."""
    ctx.simulate_apps([])
    dj.run("play tame impala on spotify")
    assert _opened_urls, "No URL was opened"
    assert "spotify.com" in _opened_urls[-1], \
        f"Expected Spotify URL, got: {_opened_urls[-1]}"

def test_provider_override_youtube():
    """'play tame impala on youtube' should use YouTube (not Music)."""
    ctx.simulate_apps([])
    dj.run("play tame impala on youtube")
    assert _opened_urls, "No URL was opened"
    url = _opened_urls[-1]
    assert "youtube.com" in url and "music.youtube.com" not in url, \
        f"Expected YouTube URL (not Music), got: {url}"

def test_vibe_chill_resolves():
    """'play something chill' should resolve to a lofi search."""
    ctx.simulate_apps([])
    search, provider, is_vibe = dj._parse_query("play something chill")
    assert is_vibe, "Expected vibe=True for 'something chill'"
    assert "lofi" in search.lower() or "chill" in search.lower(), \
        f"Unexpected search for 'chill' vibe: {search}"

def test_vibe_hype_resolves():
    """'hype me up' should resolve to a workout/hype search."""
    ctx.simulate_apps([])
    search, provider, is_vibe = dj._parse_query("hype me up")
    assert is_vibe, f"Expected vibe=True — got is_vibe={is_vibe}, search='{search}'"
    assert "hype" in search.lower() or "workout" in search.lower(), \
        f"Unexpected search for 'hype' vibe: {search}"

def test_ambiguous_morning_defaults_to_morning_vibe():
    """'play some music' at 7am → morning vibe search."""
    ctx.simulate_time(7)
    search, provider, is_vibe = dj._parse_query("play some music")
    assert is_vibe, "Expected vibe=True for ambiguous request"
    assert "morning" in search.lower() or "acoustic" in search.lower() \
           or "coffee" in search.lower(), \
        f"Expected morning vibe at 7am, got: {search}"

def test_ambiguous_late_night_defaults_to_night_vibe():
    """'play some music' at 11pm → late night vibe."""
    ctx.simulate_time(23)
    search, provider, is_vibe = dj._parse_query("play some music")
    assert is_vibe, "Expected vibe=True"
    assert "late night" in search.lower() or "lofi" in search.lower(), \
        f"Expected late night vibe at 11pm, got: {search}"

def test_specific_query_not_treated_as_vibe():
    """'play bohemian rhapsody' is specific — should NOT be vibe."""
    search, provider, is_vibe = dj._parse_query("play bohemian rhapsody")
    assert not is_vibe, "Should not be vibe for specific song"
    assert "bohemian" in search.lower(), f"Song not in query: {search}"

def test_switch_provider_persists():
    """'switch to youtube' should change default provider in config."""
    dj.run("switch to youtube")
    cfg = dj._load_cfg()
    assert cfg["default_provider"] == "youtube", \
        f"Expected youtube, got {cfg['default_provider']}"
    # Reset
    cfg["default_provider"] = "youtube_music"
    dj._save_cfg(cfg)

def test_dj_mode_toggle():
    """DJ mode should toggle on and off."""
    dj.run("dj mode on")
    assert dj._is_dj_mode(), "DJ mode should be on"
    dj.run("dj mode off")
    assert not dj._is_dj_mode(), "DJ mode should be off"

def test_queue_add():
    """Queue a song without playing it."""
    dj.run("queue tame impala")
    assert len(dj._queue) == 1, f"Expected 1 item in queue, got {len(dj._queue)}"
    assert "tame impala" in dj._queue[0]["query"].lower(), \
        f"Wrong item in queue: {dj._queue[0]}"

def test_queue_multiple():
    """Queue multiple songs."""
    dj.run("queue tame impala")
    dj.run("queue daft punk")
    dj.run("queue arctic monkeys")
    assert len(dj._queue) == 3, f"Expected 3 items, got {len(dj._queue)}"

def test_queue_play_next():
    """Play from queue removes item and opens URL."""
    dj._queue.append({"query": "tame impala", "provider": "youtube_music",
                       "added_at": "21:00"})
    dj.run("play queue")
    assert len(dj._queue) == 0, "Queue should be empty after playing"
    assert _opened_urls, "Should have opened a URL"
    assert "music.youtube.com" in _opened_urls[-1]

def test_queue_clear():
    """Clear queue empties it."""
    dj._queue.extend([
        {"query": "song1", "provider": "youtube_music", "added_at": "21:00"},
        {"query": "song2", "provider": "youtube_music", "added_at": "21:01"},
    ])
    dj.run("clear the queue")
    assert len(dj._queue) == 0, "Queue should be empty"

def test_pattern_learning_records_play():
    """Playing music records to dj_patterns in context_patterns.json."""
    ctx.simulate_time(22)  # late_night
    dj.run("play some lofi")
    patterns = dj._load_patterns()
    dj_pats  = patterns.get("dj_patterns", {})
    assert "late_night" in dj_pats, "Should have late_night pattern"
    assert dj_pats["late_night"]["count"] >= 1, "Count should be >= 1"

def test_learned_pattern_overrides_default():
    """After 3+ plays of same query at a time, it becomes the default vibe."""
    ctx.simulate_time(22)  # late_night
    # Simulate 5 prior plays of "ambient chill playlist"
    patterns = dj._load_patterns()
    patterns.setdefault("dj_patterns", {})["late_night"] = {
        "plays": ["ambient chill playlist"] * 5,
        "count": 5,
    }
    dj._save_patterns(patterns)
    search = dj._time_vibe()
    assert search == "ambient chill playlist", \
        f"Expected learned pattern, got: {search}"
    # Cleanup
    patterns = dj._load_patterns()
    patterns.get("dj_patterns", {}).pop("late_night", None)
    dj._save_patterns(patterns)

def test_be_my_dj_activates():
    """'be my dj' should activate DJ mode."""
    dj.run("be my dj")
    assert dj._is_dj_mode(), "DJ mode should be on after 'be my dj'"

def test_youtube_music_url_format():
    """YouTube Music URL should use music.youtube.com/search?q=."""
    url = dj._get_provider_url("youtube_music")
    assert "music.youtube.com" in url, f"Wrong URL: {url}"

def test_spotify_url_format():
    """Spotify URL should use open.spotify.com/search/."""
    url = dj._get_provider_url("spotify")
    assert "open.spotify.com" in url, f"Wrong URL: {url}"

def test_play_encodes_spaces():
    """Multi-word queries should be URL-encoded."""
    dj.run("play the beatles abbey road")
    assert _opened_urls, "No URL opened"
    url = _opened_urls[-1]
    assert "beatles" in url.lower(), f"Artist not in URL: {url}"
    assert " " not in url, f"Spaces not encoded in URL: {url}"


# ── Test registry ─────────────────────────────────────────────────────────────

TESTS = [
    DJTest("Default provider is YouTube Music",       test_default_provider_youtube_music,
           "No apps open → should default to youtube_music"),
    DJTest("Spotify detected when open",              test_spotify_detected_when_open,
           "spotify.exe running → provider = spotify"),
    DJTest("Browser open uses YouTube Music",         test_browser_open_uses_youtube_music,
           "opera.exe open → still defaults to youtube_music"),
    DJTest("Play opens YouTube Music URL",            test_play_opens_youtube_music_url,
           "'play tame impala' → music.youtube.com search"),
    DJTest("Provider override: Spotify",              test_provider_override_spotify,
           "'play X on spotify' → open.spotify.com"),
    DJTest("Provider override: YouTube",              test_provider_override_youtube,
           "'play X on youtube' → youtube.com (not music)"),
    DJTest("Vibe 'chill' resolves correctly",         test_vibe_chill_resolves,
           "'something chill' → lofi search query"),
    DJTest("Vibe 'hype' resolves correctly",          test_vibe_hype_resolves,
           "'hype me up' → workout/hype query"),
    DJTest("Morning time → morning vibe",             test_ambiguous_morning_defaults_to_morning_vibe,
           "7am ambiguous play → morning coffee acoustic"),
    DJTest("Late night → late night vibe",            test_ambiguous_late_night_defaults_to_night_vibe,
           "11pm ambiguous play → late night lofi"),
    DJTest("Specific song not vibe",                  test_specific_query_not_treated_as_vibe,
           "'bohemian rhapsody' → is_vibe=False"),
    DJTest("Switch provider persists to config",      test_switch_provider_persists,
           "'switch to youtube' → saves to dj_config.json"),
    DJTest("DJ mode toggles on/off",                  test_dj_mode_toggle,
           "on → off cycle"),
    DJTest("Queue add",                               test_queue_add,
           "'queue tame impala' → 1 item in queue"),
    DJTest("Queue multiple items",                    test_queue_multiple,
           "3 queue commands → 3 items"),
    DJTest("Queue play next removes item",            test_queue_play_next,
           "'play queue' → opens URL, empties queue"),
    DJTest("Queue clear empties queue",               test_queue_clear,
           "'clear the queue' → []"),
    DJTest("Pattern learning records play",           test_pattern_learning_records_play,
           "play at 11pm → dj_patterns.late_night.count >= 1"),
    DJTest("Learned pattern overrides time default",  test_learned_pattern_overrides_default,
           "5 plays of X at 11pm → X becomes the late night default"),
    DJTest("'be my dj' activates DJ mode",            test_be_my_dj_activates,
           "natural language activation"),
    DJTest("YouTube Music URL format",                test_youtube_music_url_format,
           "provider URL contains music.youtube.com"),
    DJTest("Spotify URL format",                      test_spotify_url_format,
           "provider URL contains open.spotify.com"),
    DJTest("Multi-word query URL-encoded",            test_play_encodes_spaces,
           "spaces become %20 or + in URL"),
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run(verbose=False):
    _ansi()
    total = passed = failed = 0
    results = []

    print(f"\n{BOLD}  JARVIS DJ System Tests{RESET}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    for test in TESTS:
        total += 1
        ok, err = test.run()
        if ok:
            passed += 1
            marker = f"{GREEN}PASS{RESET}"
        else:
            failed += 1
            marker = f"{RED}FAIL{RESET}"

        print(f"    {marker}  {test.name}")
        if verbose or not ok:
            print(f"           {DIM}{test.description}{RESET}")
        if not ok:
            print(f"           {RED}{err}{RESET}")

        results.append({"name": test.name, "passed": ok, "error": err})

    pct = int(passed / total * 100) if total else 0
    bf  = int(40 * passed / total) if total else 0
    bar = f"{GREEN}{'█'*bf}{RESET}{DIM}{'░'*(40-bf)}{RESET}"

    print(f"\n  {BOLD}Results: {passed}/{total} passed  ({pct}%){RESET}")
    print(f"  [{bar}]")

    failures = [r for r in results if not r["passed"]]
    if failures:
        print(f"\n  {RED}{BOLD}Failed:{RESET}")
        for r in failures:
            print(f"    {RED}✗{RESET}  {r['name']}")
            if r["error"]:
                print(f"       {DIM}{r['error']}{RESET}")

    report_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(report_dir, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(report_dir, f"dj_report_{ts}.json")
    with open(path, "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(),
                   "total": total, "passed": passed,
                   "failed": failed, "results": results}, f, indent=2)
    print(f"\n  {DIM}Report saved: {path}{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    run(verbose=args.verbose)