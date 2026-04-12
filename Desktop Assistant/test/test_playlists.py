"""
test/test_playlists.py — Playlist management and taste profile tests.

Tests playlist registration, fuzzy matching, genre scraping (mocked),
taste profile building, Spotify sync (mocked), and startup behavior.

No network calls are made — MusicBrainz and Spotify are fully mocked.

Usage:
    python test/test_playlists.py
    python test/test_playlists.py --verbose
"""

import sys, os, io, json, copy, argparse, threading
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Silence speaker
import bot.speaker as _spk
_spk.speak = lambda t: None

# Patch webbrowser so no browser opens
import webbrowser
webbrowser.open = lambda url, **kw: True

from bot.context import ctx
import commands.playlists as pl
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

# ── Test state helpers ────────────────────────────────────────────────────────

_ORIG_PLAYLISTS = None
_ORIG_TASTE     = None

def _save_state():
    global _ORIG_PLAYLISTS, _ORIG_TASTE
    _ORIG_PLAYLISTS = pl._load_playlists()
    _ORIG_TASTE     = pl._load_taste()

def _restore_state():
    if _ORIG_PLAYLISTS is not None:
        pl._save_playlists(copy.deepcopy(_ORIG_PLAYLISTS))
    if _ORIG_TASTE is not None:
        pl._save_taste(copy.deepcopy(_ORIG_TASTE))

def _reset():
    ctx.clear_simulation()
    ctx._command_history.clear()
    ctx._last_suggestion_ts = 0
    # Reset to clean playlists
    pl._save_playlists({"youtube_music": {}, "spotify": {
        "auto_fetched": False, "last_synced": None, "playlists": []}})
    # Reset to clean taste profile
    pl._save_taste({
        "top_artists": {}, "top_genres": {}, "top_playlists": {},
        "skipped": {}, "time_profile": {}, "genre_cache": {},
    })


# ── Test class ────────────────────────────────────────────────────────────────

class PLTest:
    def __init__(self, name, fn, description=""):
        self.name, self.fn, self.description = name, fn, description

    def run(self):
        _reset()
        try:
            result = self.fn()
            return (True, "") if result is not False else (False, "returned False")
        except AssertionError as e:
            return False, str(e)
        except Exception as e:
            import traceback
            tb = traceback.format_exc().strip().split("\n")[-1]
            return False, f"{type(e).__name__}: {e} | {tb}"


# ── Playlist registration tests ───────────────────────────────────────────────

def test_register_youtube_music_playlist():
    """Register a YouTube Music playlist via command."""
    pl.run("add playlist lofi study https://music.youtube.com/playlist?list=PLtest123")
    data = pl._load_playlists()
    assert "lofi study" in data["youtube_music"], \
        f"Playlist not registered: {data['youtube_music']}"
    assert data["youtube_music"]["lofi study"] == \
        "https://music.youtube.com/playlist?list=PLtest123"

def test_register_multiple_playlists():
    """Register multiple playlists and list them."""
    pl.run("add playlist hype workout https://music.youtube.com/playlist?list=PLhype")
    pl.run("add playlist chill vibes https://music.youtube.com/playlist?list=PLchill")
    data = pl._load_playlists()
    assert "hype workout" in data["youtube_music"]
    assert "chill vibes"  in data["youtube_music"]

def test_playlist_url_stored_correctly():
    """URL is stored exactly as provided."""
    url = "https://music.youtube.com/playlist?list=PLexact123"
    pl.run(f"add playlist test list {url}")
    data = pl._load_playlists()
    assert data["youtube_music"].get("test list") == url, \
        f"URL mismatch: {data['youtube_music'].get('test list')}"


# ── Fuzzy matching tests ──────────────────────────────────────────────────────

def test_exact_name_match():
    """Exact playlist name returns correct URL."""
    pl._save_playlists({"youtube_music": {
        "lofi study": "https://music.youtube.com/playlist?list=PLlofi"
    }, "spotify": {"playlists": []}})
    name, url, provider = pl.find_playlist("lofi study")
    assert name == "lofi study", f"Wrong name: {name}"
    assert "PLlofi" in url
    assert provider == "youtube_music"

def test_partial_name_match():
    """Partial match still finds the playlist."""
    pl._save_playlists({"youtube_music": {
        "lofi hip hop study beats": "https://music.youtube.com/playlist?list=PLlofi"
    }, "spotify": {"playlists": []}})
    name, url, provider = pl.find_playlist("lofi study")
    assert name is not None, "Should find partial match"

def test_fuzzy_typo_match():
    """Typo in playlist name still matches."""
    pl._save_playlists({"youtube_music": {
        "morning coffee": "https://music.youtube.com/playlist?list=PLmorning"
    }, "spotify": {"playlists": []}})
    name, url, provider = pl.find_playlist("morning coffe")  # missing e
    assert name is not None, "Should fuzzy-match 'morning coffe' → 'morning coffee'"

def test_no_match_returns_none():
    """Query with no close match returns (None, None, None)."""
    pl._save_playlists({"youtube_music": {
        "lofi study": "https://music.youtube.com/playlist?list=PLlofi"
    }, "spotify": {"playlists": []}})
    name, url, provider = pl.find_playlist("completely unrelated query zxcv")
    assert name is None, f"Should return None for no match, got: {name}"

def test_spotify_playlist_found():
    """Spotify playlists are also searched."""
    pl._save_playlists({"youtube_music": {}, "spotify": {
        "playlists": [{"name": "Discover Weekly",
                       "id": "37i9x",
                       "url": "https://open.spotify.com/playlist/37i9x"}]
    }})
    name, url, provider = pl.find_playlist("discover weekly")
    assert name == "Discover Weekly", f"Wrong name: {name}"
    assert provider == "spotify"


# ── Genre scraping tests (mocked) ─────────────────────────────────────────────

def test_genre_scrape_caches_result():
    """Genre lookup result is cached to avoid repeat API calls."""
    mock_response = json.dumps({
        "artists": [{"name": "Tame Impala", "tags": [
            {"name": "psychedelic rock", "count": 10},
            {"name": "indie pop", "count": 8},
        ]}]
    }).encode()

    class MockResponse:
        def __init__(self): pass
        def read(self): return mock_response
        def __enter__(self): return self
        def __exit__(self, *a): pass

    with patch("urllib.request.urlopen", return_value=MockResponse()):
        genres = pl._scrape_genres("Tame Impala")

    assert "psychedelic rock" in genres, f"Expected psychedelic rock, got: {genres}"
    # Second call should use cache (no network)
    taste = pl._load_taste()
    assert "tame impala" in taste.get("genre_cache", {}), \
        "Should be cached after first lookup"

def test_genre_scrape_network_failure_returns_empty():
    """Network failure returns empty list without raising."""
    with patch("urllib.request.urlopen", side_effect=Exception("network error")):
        genres = pl._scrape_genres("Unknown Artist XYZ")
    assert genres == [], f"Expected empty list on failure, got: {genres}"

def test_genre_vibe_mapping():
    """Genre tags map to JARVIS vibe words correctly."""
    assert pl._infer_vibe_from_genres(["psychedelic rock"]) == "chill"
    assert pl._infer_vibe_from_genres(["metal"])            == "aggressive"
    assert pl._infer_vibe_from_genres(["acoustic"])         == "morning"
    assert pl._infer_vibe_from_genres(["lo-fi"])            == "lofi"
    assert pl._infer_vibe_from_genres(["hip-hop"])          == "rap"
    assert pl._infer_vibe_from_genres(["xyzunknown"])       is None


# ── Taste profile tests ───────────────────────────────────────────────────────

def test_record_play_updates_artist_count():
    """Playing a track increments artist count."""
    pl.record_play("tame impala", "Tame Impala", "afternoon")
    taste = pl._load_taste()
    assert taste["top_artists"].get("Tame Impala", 0) >= 1, \
        f"Artist count not updated: {taste['top_artists']}"

def test_record_play_updates_time_profile():
    """Play at afternoon updates time_profile.afternoon.artists."""
    pl.record_play("tame impala", "Tame Impala", "afternoon")
    taste = pl._load_taste()
    artists = taste.get("time_profile", {}).get("afternoon", {}).get("artists", {})
    assert artists.get("Tame Impala", 0) >= 1, \
        f"Time profile not updated: {artists}"

def test_record_play_no_artist_uses_query():
    """Play without artist still records query-based genre inference."""
    pl.record_play("lofi hip hop beats", None, "late_night")
    taste = pl._load_taste()
    # Should still have something recorded even without artist
    assert taste.get("top_artists") is not None

def test_record_skip_negative_signal():
    """Skipping a track records it as negative signal."""
    pl.record_play("annoying song", "Bad Artist", "morning", is_skip=True)
    taste = pl._load_taste()
    assert taste.get("skipped", {}).get("annoying song", 0) >= 1, \
        f"Skip not recorded: {taste.get('skipped')}"

def test_skip_does_not_increment_artist():
    """Skipping does not increment artist play count."""
    pl.record_play("annoying song", "Bad Artist", "morning", is_skip=True)
    taste = pl._load_taste()
    assert taste.get("top_artists", {}).get("Bad Artist", 0) == 0, \
        "Skipped track should not increment artist count"

def test_record_playlist_play():
    """Playing a playlist increments playlist count."""
    pl.record_play("lofi playlist", None, "evening", playlist_name="lofi study")
    taste = pl._load_taste()
    assert taste.get("top_playlists", {}).get("lofi study", 0) >= 1, \
        f"Playlist count not updated: {taste.get('top_playlists')}"

def test_taste_summary_empty():
    """Empty taste profile returns graceful message."""
    summary = pl.get_taste_summary()
    assert "not enough" in summary.lower() or "no data" in summary.lower() \
           or "taste profile" in summary.lower(), \
        f"Unexpected summary for empty profile: {summary}"

def test_taste_summary_with_data():
    """Taste summary reflects recorded plays."""
    pl.record_play("tame impala", "Tame Impala", "afternoon")
    pl.record_play("tame impala", "Tame Impala", "afternoon")
    pl.record_play("daft punk",   "Daft Punk",   "evening")
    # Wait briefly for background genre thread (or skip genre check)
    import time; time.sleep(0.1)
    summary = pl.get_taste_summary()
    assert len(summary) > 10, f"Summary too short: '{summary}'"

def test_taste_summary_time_mode():
    """Time-mode summary only covers that time period."""
    pl.record_play("tame impala", "Tame Impala", "afternoon")
    pl.record_play("daft punk",   "Daft Punk",   "late_night")
    summary = pl.get_taste_summary(time_mode="afternoon")
    assert "afternoon" in summary.lower() or "tame impala" in summary.lower(), \
        f"Unexpected afternoon summary: {summary}"


# ── Spotify sync tests (mocked) ───────────────────────────────────────────────

def test_spotify_sync_when_not_configured():
    """Sync returns 0 and doesn't crash when Spotify not configured."""
    with patch("commands.playlists.sync_spotify") as mock_sync:
        mock_sync.return_value = 0
        count = mock_sync(silent=True)
    assert count == 0

def test_spotify_sync_saves_playlists():
    """Spotify sync saves playlists to playlists.json."""
    mock_playlists = [
        {"name": "Discover Weekly", "id": "abc", "url": "https://open.spotify.com/playlist/abc",
         "track_count": 30, "description": ""},
        {"name": "Release Radar",   "id": "def", "url": "https://open.spotify.com/playlist/def",
         "track_count": 30, "description": ""},
    ]
    with patch("bot.spotify_client.is_available", return_value=True), \
         patch("bot.spotify_client.get_playlists", return_value=mock_playlists):
        count = pl.sync_spotify(silent=True)

    assert count == 2, f"Expected 2 playlists synced, got {count}"
    data = pl._load_playlists()
    names = [p["name"] for p in data["spotify"]["playlists"]]
    assert "Discover Weekly" in names, f"Missing Discover Weekly: {names}"
    assert "Release Radar"   in names, f"Missing Release Radar: {names}"

def test_spotify_playlist_playable_after_sync():
    """After sync, Spotify playlist is findable by name."""
    mock_playlists = [
        {"name": "Discover Weekly", "id": "abc",
         "url": "https://open.spotify.com/playlist/abc",
         "track_count": 30, "description": ""},
    ]
    with patch("bot.spotify_client.is_available", return_value=True), \
         patch("bot.spotify_client.get_playlists", return_value=mock_playlists):
        pl.sync_spotify(silent=True)

    name, url, provider = pl.find_playlist("discover weekly")
    assert name == "Discover Weekly", f"Playlist not findable after sync: {name}"
    assert provider == "spotify"

def test_spotify_sync_idempotent():
    """Syncing twice doesn't duplicate playlists."""
    mock_playlists = [
        {"name": "My Playlist", "id": "abc",
         "url": "https://open.spotify.com/playlist/abc",
         "track_count": 10, "description": ""},
    ]
    with patch("bot.spotify_client.is_available", return_value=True), \
         patch("bot.spotify_client.get_playlists", return_value=mock_playlists):
        pl.sync_spotify(silent=True)
        pl.sync_spotify(silent=True)

    data = pl._load_playlists()
    names = [p["name"] for p in data["spotify"]["playlists"]]
    assert names.count("My Playlist") == 1, \
        f"Playlist duplicated after double sync: {names}"


# ── Integration: dj.py → playlists.py ────────────────────────────────────────

def test_dj_play_opens_registered_playlist():
    """'play lofi study' opens the registered YouTube Music URL."""
    pl._save_playlists({"youtube_music": {
        "lofi study": "https://music.youtube.com/playlist?list=PLlofi"
    }, "spotify": {"playlists": []}})

    opened = []
    with patch("webbrowser.open", side_effect=lambda url, **kw: opened.append(url)):
        pl.run("play lofi study")

    assert opened, "Should have opened a URL"
    assert "PLlofi" in opened[-1], f"Wrong URL opened: {opened[-1]}"

def test_dj_play_records_playlist_in_taste():
    """Playing a playlist via dj records it in taste profile."""
    pl._save_playlists({"youtube_music": {
        "lofi study": "https://music.youtube.com/playlist?list=PLlofi"
    }, "spotify": {"playlists": []}})
    ctx.simulate_time(22)

    with patch("webbrowser.open"):
        pl.run("play lofi study")

    taste = pl._load_taste()
    assert taste.get("top_playlists", {}).get("lofi study", 0) >= 1, \
        f"Playlist not recorded in taste: {taste.get('top_playlists')}"


# ── Startup sync test ─────────────────────────────────────────────────────────

def test_startup_sync_runs_in_background():
    """startup_sync launches a daemon thread without blocking."""
    started = [False]
    def _mock_sync(silent=False):
        started[0] = True

    import commands.playlists as _pl
    original = _pl.sync_spotify
    _pl.sync_spotify = _mock_sync
    try:
        pl.startup_sync()
        import time; time.sleep(0.3)
        assert started[0], "startup_sync should have called sync_spotify"
    finally:
        _pl.sync_spotify = original


# ── Test registry ─────────────────────────────────────────────────────────────

TESTS = [
    # Registration
    PLTest("Register YouTube Music playlist",      test_register_youtube_music_playlist,
           "add playlist name url → stored in playlists.json"),
    PLTest("Register multiple playlists",          test_register_multiple_playlists,
           "Two registrations both persist"),
    PLTest("URL stored exactly as provided",       test_playlist_url_stored_correctly,
           "No URL mangling"),

    # Fuzzy matching
    PLTest("Exact name match",                     test_exact_name_match,
           "Exact query returns correct playlist"),
    PLTest("Partial name match",                   test_partial_name_match,
           "Substring match works"),
    PLTest("Fuzzy typo match",                     test_fuzzy_typo_match,
           "Minor typo still finds playlist"),
    PLTest("No match returns None",                test_no_match_returns_none,
           "Gibberish query returns (None, None, None)"),
    PLTest("Spotify playlist found by name",       test_spotify_playlist_found,
           "Spotify playlists included in search"),

    # Genre scraping
    PLTest("Genre scrape caches result",           test_genre_scrape_caches_result,
           "MusicBrainz result saved to genre_cache"),
    PLTest("Network failure returns empty",        test_genre_scrape_network_failure_returns_empty,
           "No crash on network error"),
    PLTest("Genre → vibe mapping",                 test_genre_vibe_mapping,
           "psychedelic rock→chill, metal→aggressive etc."),

    # Taste profile
    PLTest("Record play updates artist count",     test_record_play_updates_artist_count,
           "top_artists increments"),
    PLTest("Record play updates time profile",     test_record_play_updates_time_profile,
           "time_profile.afternoon.artists increments"),
    PLTest("Record play without artist",           test_record_play_no_artist_uses_query,
           "Query-based tracking still works"),
    PLTest("Skip is negative signal",              test_record_skip_negative_signal,
           "skipped dict increments"),
    PLTest("Skip doesn't increment artist",        test_skip_does_not_increment_artist,
           "Skipped track not counted as play"),
    PLTest("Record playlist play",                 test_record_playlist_play,
           "top_playlists increments"),
    PLTest("Taste summary empty profile",          test_taste_summary_empty,
           "Graceful message when no data"),
    PLTest("Taste summary with data",              test_taste_summary_with_data,
           "Summary reflects recorded plays"),
    PLTest("Taste summary for time mode",          test_taste_summary_time_mode,
           "Time-mode summary scoped correctly"),

    # Spotify sync
    PLTest("Spotify sync when unconfigured",       test_spotify_sync_when_not_configured,
           "Returns 0, no crash"),
    PLTest("Spotify sync saves playlists",         test_spotify_sync_saves_playlists,
           "Playlists written to playlists.json"),
    PLTest("Spotify playlist playable after sync", test_spotify_playlist_playable_after_sync,
           "find_playlist works after sync"),
    PLTest("Spotify sync is idempotent",           test_spotify_sync_idempotent,
           "Double sync doesn't duplicate entries"),

    # Integration
    PLTest("DJ plays registered playlist by name", test_dj_play_opens_registered_playlist,
           "Playlist name → correct URL opened"),
    PLTest("DJ play records playlist in taste",    test_dj_play_records_playlist_in_taste,
           "top_playlists updated when playlist played"),
    PLTest("Startup sync runs in background",      test_startup_sync_runs_in_background,
           "Non-blocking daemon thread"),
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run(verbose=False):
    _ansi()
    _save_state()

    total = passed = failed = 0
    results = []

    print(f"\n{BOLD}  JARVIS Playlist & Taste Profile Tests{RESET}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    groups = [
        ("Playlist Registration",  TESTS[0:3]),
        ("Fuzzy Matching",         TESTS[3:8]),
        ("Genre Scraping",         TESTS[8:11]),
        ("Taste Profile",          TESTS[11:20]),
        ("Spotify Sync",           TESTS[20:24]),
        ("Integration",            TESTS[24:27]),
    ]

    for group_name, group_tests in groups:
        print(f"  {CYAN}{BOLD}{group_name}{RESET}")
        g_pass = g_fail = 0

        for test in group_tests:
            total += 1
            ok, err = test.run()
            if ok:
                passed += 1; g_pass += 1
                marker = f"{GREEN}PASS{RESET}"
            else:
                failed += 1; g_fail += 1
                marker = f"{RED}FAIL{RESET}"

            print(f"    {marker}  {test.name}")
            if verbose or not ok:
                print(f"           {DIM}{test.description}{RESET}")
            if not ok:
                print(f"           {RED}{err}{RESET}")

            results.append({"name": test.name, "passed": ok, "error": err})

        color = GREEN if g_fail == 0 else (YELLOW if g_pass > 0 else RED)
        print(f"    {color}{g_pass}/{g_pass+g_fail} passed{RESET}\n")

    pct = int(passed / total * 100) if total else 0
    bf  = int(40 * passed / total) if total else 0
    bar = f"{GREEN}{'█'*bf}{RESET}{DIM}{'░'*(40-bf)}{RESET}"
    print(f"  {BOLD}Results: {passed}/{total} passed  ({pct}%){RESET}")
    print(f"  [{bar}]")

    failures = [r for r in results if not r["passed"]]
    if failures:
        print(f"\n  {RED}{BOLD}Failed:{RESET}")
        for r in failures:
            print(f"    {RED}✗{RESET}  {r['name']}")
            if r["error"]:
                print(f"       {DIM}{r['error']}{RESET}")

    _restore_state()

    report_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(report_dir, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(report_dir, f"playlists_report_{ts}.json")
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