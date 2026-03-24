"""
commands/playlists.py — Playlist management and taste profile.

Handles:
  - YouTube Music playlist registration (manual URL → name)
  - Spotify playlist sync (auto via API)
  - Genre scraping from MusicBrainz (free, no key)
  - Taste profile building from play history
  - Startup sync

Triggers: see commands.json
"""

import os, re, json, time, threading, urllib.parse, urllib.request
from datetime import datetime
from bot.speaker import speak
from bot.context import ctx

_ROOT           = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PLAYLISTS_PATH = os.path.join(_ROOT, "config", "playlists.json")
_TASTE_PATH     = os.path.join(_ROOT, "config", "taste_profile.json")

# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_playlists() -> dict:
    try:
        with open(_PLAYLISTS_PATH) as f: return json.load(f)
    except Exception: return {"youtube_music": {}, "spotify": {"playlists": []}}

def _save_playlists(data: dict):
    try:
        with open(_PLAYLISTS_PATH, "w") as f: json.dump(data, f, indent=2)
    except Exception: pass

def _load_taste() -> dict:
    try:
        with open(_TASTE_PATH) as f: return json.load(f)
    except Exception:
        return {"top_artists": {}, "top_genres": {}, "top_playlists": {},
                "skipped": {}, "time_profile": {}, "genre_cache": {}}

def _save_taste(data: dict):
    try:
        data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(_TASTE_PATH, "w") as f: json.dump(data, f, indent=2)
    except Exception: pass

# ── Genre scraping (MusicBrainz — free, no key) ───────────────────────────────

def _scrape_genres(artist: str) -> list[str]:
    """
    Look up an artist on MusicBrainz and return their genre/tag list.
    Results cached in taste_profile.json['genre_cache'] to avoid repeat calls.
    Returns [] if not found or network unavailable.
    """
    taste = _load_taste()
    cache = taste.setdefault("genre_cache", {})
    key   = artist.lower().strip()

    if key in cache:
        return cache[key]

    try:
        encoded = urllib.parse.quote(artist)
        url = (f"https://musicbrainz.org/ws/2/artist/"
               f"?query=artist:{encoded}&fmt=json&limit=1")
        req = urllib.request.Request(url, headers={
            "User-Agent": "JARVIS/1.0 (desktop-assistant)"
        })
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())

        artists = data.get("artists", [])
        if not artists:
            cache[key] = []
            _save_taste(taste)
            return []

        top    = artists[0]
        genres = [t["name"].lower() for t in top.get("tags", [])
                  if t.get("count", 0) > 0][:5]

        cache[key] = genres
        _save_taste(taste)
        return genres

    except Exception:
        return []


def _infer_vibe_from_genres(genres: list[str]) -> str | None:
    """Map MusicBrainz genre tags to JARVIS vibe words."""
    GENRE_VIBE_MAP = {
        "lo-fi": "lofi", "lofi": "lofi", "lo fi": "lofi",
        "hip-hop": "rap", "hip hop": "rap", "rap": "rap",
        "electronic": "chill", "ambient": "ambient",
        "indie": "chill", "indie pop": "chill", "indie rock": "chill",
        "psychedelic": "chill", "psychedelic rock": "chill",
        "rock": "hype", "alternative rock": "chill",
        "metal": "aggressive", "heavy metal": "aggressive",
        "pop": "happy", "dance pop": "party", "dance": "party",
        "jazz": "jazz", "blues": "jazz",
        "classical": "classical", "piano": "classical",
        "r&b": "chill", "soul": "chill",
        "acoustic": "morning", "folk": "morning",
        "workout": "hype", "edm": "hype",
        "sleep": "sleep", "meditation": "sleep",
    }
    for g in genres:
        for key, vibe in GENRE_VIBE_MAP.items():
            if key in g:
                return vibe
    return None

# ── Taste profile update ──────────────────────────────────────────────────────

def record_play(query: str, artist: str | None, time_mode: str,
                playlist_name: str | None = None, is_skip: bool = False):
    """
    Central record-keeping for every play/skip.
    - Looks up artist genres via MusicBrainz (cached)
    - Updates top_artists, top_genres, time_profile
    - Records playlist plays
    - Records skips as negative signal
    Runs genre scrape in background thread so it never blocks playback.
    """
    taste = _load_taste()

    if is_skip:
        taste.setdefault("skipped", {})[query] = \
            taste.get("skipped", {}).get(query, 0) + 1
        _save_taste(taste)
        return

    # Playlist tracking
    if playlist_name:
        taste.setdefault("top_playlists", {})[playlist_name] = \
            taste.get("top_playlists", {}).get(playlist_name, 0) + 1

    # Artist tracking
    if artist:
        taste.setdefault("top_artists", {})[artist] = \
            taste.get("top_artists", {}).get(artist, 0) + 1
        time_p = taste.setdefault("time_profile", {}).setdefault(time_mode, {
            "artists": {}, "genres": {}})
        time_p.setdefault("artists", {})[artist] = \
            time_p["artists"].get(artist, 0) + 1

    _save_taste(taste)

    # Genre scraping in background
    if artist:
        def _bg_genre_update():
            genres = _scrape_genres(artist)
            if not genres:
                return
            t = _load_taste()
            for g in genres:
                t.setdefault("top_genres", {})[g] = \
                    t.get("top_genres", {}).get(g, 0) + 1
                time_p = t.setdefault("time_profile", {}).setdefault(time_mode, {
                    "artists": {}, "genres": {}})
                time_p.setdefault("genres", {})[g] = \
                    time_p["genres"].get(g, 0) + 1
            _save_taste(t)

        threading.Thread(target=_bg_genre_update, daemon=True).start()
    else:
        # No artist — try to infer vibe from query words directly
        query_words = query.lower().split()
        taste = _load_taste()
        for word in query_words:
            vibe = _infer_vibe_from_genres([word])
            if vibe:
                taste.setdefault("top_genres", {})[word] = \
                    taste.get("top_genres", {}).get(word, 0) + 1
                time_p = taste.setdefault("time_profile", {}).setdefault(time_mode, {
                    "artists": {}, "genres": {}})
                time_p.setdefault("genres", {})[word] = \
                    time_p["genres"].get(word, 0) + 1
        _save_taste(taste)

# ── Playlist fuzzy match ──────────────────────────────────────────────────────

def find_playlist(query: str) -> tuple[str | None, str | None, str | None]:
    """
    Fuzzy-match a query against all registered playlists.
    Returns (name, url, provider) or (None, None, None).
    """
    from difflib import SequenceMatcher
    playlists = _load_playlists()
    query_lower = query.lower().strip()
    best_score = 0.0
    best = (None, None, None)

    # YouTube Music playlists
    for name, url in playlists.get("youtube_music", {}).items():
        score = SequenceMatcher(None, query_lower, name.lower()).ratio()
        if query_lower in name.lower():
            score = 1.0
        if score > best_score:
            best_score, best = score, (name, url, "youtube_music")

    # Spotify playlists
    for pl in playlists.get("spotify", {}).get("playlists", []):
        name  = pl["name"]
        score = SequenceMatcher(None, query_lower, name.lower()).ratio()
        if query_lower in name.lower():
            score = 1.0
        if score > best_score:
            best_score, best = score, (name, pl["url"], "spotify")

    return best if best_score >= 0.5 else (None, None, None)

# ── Spotify sync ──────────────────────────────────────────────────────────────

def sync_spotify(silent: bool = False) -> int:
    """
    Pull all Spotify playlists and merge into playlists.json.
    Returns count of playlists synced. 0 if Spotify not configured.
    """
    try:
        from bot.spotify_client import is_available, get_playlists
        if not is_available():
            if not silent:
                speak("Spotify isn't set up. Run: python bot/spotify_client.py --setup")
            return 0
        spotify_playlists = get_playlists()
        if not spotify_playlists:
            if not silent: speak("No Spotify playlists found.")
            return 0
        data = _load_playlists()
        data["spotify"]["playlists"]   = spotify_playlists
        data["spotify"]["auto_fetched"] = True
        data["spotify"]["last_synced"]  = datetime.now().strftime("%Y-%m-%d %H:%M")
        _save_playlists(data)
        if not silent:
            speak(f"Synced {len(spotify_playlists)} Spotify playlists.")
        return len(spotify_playlists)
    except Exception as e:
        if not silent:
            speak("Spotify sync failed. Check your credentials.")
        return 0

def startup_sync():
    """Called on JARVIS startup — silently syncs Spotify in background."""
    threading.Thread(target=lambda: sync_spotify(silent=True), daemon=True).start()

# ── Taste summary ─────────────────────────────────────────────────────────────

def get_taste_summary(time_mode: str | None = None) -> str:
    """Return a human-readable taste summary for JARVIS to speak."""
    taste = _load_taste()

    if time_mode:
        time_p = taste.get("time_profile", {}).get(time_mode, {})
        top_artists = sorted(time_p.get("artists", {}).items(),
                             key=lambda x: x[1], reverse=True)[:3]
        top_genres  = sorted(time_p.get("genres", {}).items(),
                             key=lambda x: x[1], reverse=True)[:3]
        parts = []
        if top_artists:
            parts.append("artists: " + ", ".join(a for a, _ in top_artists))
        if top_genres:
            parts.append("genres: " + ", ".join(g for g, _ in top_genres))
        return f"At {time_mode} you tend to listen to {'; '.join(parts)}." \
               if parts else f"Not enough data yet for {time_mode}."

    top_artists = sorted(taste.get("top_artists", {}).items(),
                         key=lambda x: x[1], reverse=True)[:5]
    top_genres  = sorted(taste.get("top_genres", {}).items(),
                         key=lambda x: x[1], reverse=True)[:5]
    parts = []
    if top_artists:
        parts.append("top artists: " + ", ".join(a for a, _ in top_artists))
    if top_genres:
        parts.append("top genres: " + ", ".join(g for g, _ in top_genres))
    return "Your taste profile — " + "; ".join(parts) + "." \
           if parts else "Not enough listening data yet."

# ── Command handler ───────────────────────────────────────────────────────────

def run(query: str) -> str:
    q = query.lower().strip()

    # ── Add YouTube Music playlist ────────────────────────────────────────────
    # Use original query for URL extraction to preserve case
    raw = query.strip()
    m = re.search(r'add playlist\s+(.+?)\s+(https?://\S+)', raw, re.IGNORECASE)
    if m:
        name, url = m.group(1).strip().lower(), m.group(2).strip()
        data = _load_playlists()
        data.setdefault("youtube_music", {})[name] = url
        _save_playlists(data)
        speak(f"Registered playlist '{name}'.")
        return f"Playlist added: {name}"

    # ── List playlists ────────────────────────────────────────────────────────
    if any(x in q for x in ["my playlists", "list playlists", "show playlists"]):
        data = _load_playlists()
        yt   = list(data.get("youtube_music", {}).keys())
        sp   = [p["name"] for p in data.get("spotify", {}).get("playlists", [])]
        all_pl = yt + sp
        if not all_pl:
            speak("No playlists registered yet.")
            return "No playlists."
        speak(f"You have {len(all_pl)} playlists: {', '.join(all_pl[:5])}"
              + (f" and {len(all_pl)-5} more." if len(all_pl) > 5 else "."))
        return f"{len(all_pl)} playlists listed."

    # ── Sync Spotify ──────────────────────────────────────────────────────────
    if any(x in q for x in ["sync spotify", "update spotify", "refresh spotify"]):
        count = sync_spotify()
        return f"Synced {count} Spotify playlists."

    # ── Taste profile ─────────────────────────────────────────────────────────
    if any(x in q for x in ["my taste", "what do i listen to",
                              "what's my most played", "taste profile",
                              "my music profile"]):
        time_mode = None
        for mode in ["morning", "midday", "afternoon", "evening", "night", "late_night"]:
            if mode.replace("_", " ") in q:
                time_mode = mode
                break
        summary = get_taste_summary(time_mode)
        speak(summary)
        return summary

    # ── Play playlist by name (fuzzy) ─────────────────────────────────────────
    for prefix in ["play playlist", "shuffle playlist", "play", "shuffle"]:
        if q.startswith(prefix):
            name_query = q[len(prefix):].strip()
            pl_name, pl_url, pl_provider = find_playlist(name_query)
            if pl_name:
                import webbrowser as wb
                wb.open(pl_url)
                speak(f"Playing {pl_name}.")
                record_play(pl_name, None, ctx.get_time_mode(),
                            playlist_name=pl_name)
                return f"Playing playlist: {pl_name}"
            break

    speak("I couldn't find that playlist. Try 'add playlist name url' to register one.")
    return "Playlist not found."