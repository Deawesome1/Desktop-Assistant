"""
bot/spotify_client.py — Spotify Web API wrapper.

Graceful fallback: if no credentials, all methods return None/empty
without raising. JARVIS continues with YouTube Music.

Setup (one-time):
  python bot/spotify_client.py --setup
"""

import os, sys, json, time, base64, webbrowser
import urllib.parse, urllib.request, urllib.error
from datetime import datetime

_ROOT       = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_CREDS_PATH = os.path.join(_ROOT, "config", "spotify_creds.json")
_TOKEN_PATH = os.path.join(_ROOT, "config", "spotify_token.json")
_REDIRECT   = "http://localhost:8888/callback"
_SCOPE      = ("user-read-playback-state user-read-currently-playing "
               "playlist-read-private playlist-read-collaborative")


def _load_creds() -> dict:
    try:
        with open(_CREDS_PATH) as f: return json.load(f)
    except Exception: return {}

def _load_token() -> dict:
    try:
        with open(_TOKEN_PATH) as f: return json.load(f)
    except Exception: return {}

def _save_token(data: dict):
    try:
        with open(_TOKEN_PATH, "w") as f: json.dump(data, f, indent=2)
    except Exception: pass

def _is_configured() -> bool:
    c = _load_creds()
    return bool(c.get("client_id") and c.get("client_secret"))

def _refresh_token() -> str | None:
    token = _load_token(); creds = _load_creds()
    if not token.get("refresh_token") or not creds.get("client_id"):
        return None
    try:
        auth = base64.b64encode(
            f"{creds['client_id']}:{creds['client_secret']}".encode()).decode()
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        }).encode()
        req = urllib.request.Request(
            "https://accounts.spotify.com/api/token", data=data,
            headers={"Authorization": f"Basic {auth}",
                     "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=10) as r:
            new = json.loads(r.read())
        new["refresh_token"] = token["refresh_token"]
        new["expires_at"]    = time.time() + new.get("expires_in", 3600)
        _save_token(new)
        return new["access_token"]
    except Exception: return None

def _get_access_token() -> str | None:
    token = _load_token()
    if not token: return None
    if time.time() < token.get("expires_at", 0) - 60:
        return token.get("access_token")
    return _refresh_token()

def _api(endpoint: str) -> dict | list | None:
    token = _get_access_token()
    if not token: return None
    try:
        req = urllib.request.Request(
            f"https://api.spotify.com/v1/{endpoint}",
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception: return None

# ── Public API ────────────────────────────────────────────────────────────────

def is_available() -> bool:
    return _is_configured() and bool(_get_access_token())

def get_playlists() -> list[dict]:
    if not _is_configured(): return []
    result, endpoint = [], "me/playlists?limit=50"
    while endpoint:
        data = _api(endpoint)
        if not data: break
        for item in data.get("items", []):
            if item:
                result.append({
                    "name":        item["name"],
                    "id":          item["id"],
                    "url":         item["external_urls"]["spotify"],
                    "track_count": item["tracks"]["total"],
                    "description": item.get("description", ""),
                })
        nxt = data.get("next")
        endpoint = nxt.replace("https://api.spotify.com/v1/", "") if nxt else None
    return result

def get_now_playing() -> dict | None:
    data = _api("me/player/currently-playing")
    if not data or not data.get("item"): return None
    item = data["item"]
    return {
        "title":      item["name"],
        "artist":     ", ".join(a["name"] for a in item.get("artists", [])),
        "album":      item["album"]["name"],
        "is_playing": data.get("is_playing", False),
    }

def get_recently_played(limit: int = 20) -> list[dict]:
    data = _api(f"me/player/recently-played?limit={limit}")
    if not data: return []
    result = []
    for item in data.get("items", []):
        track = item.get("track", {})
        result.append({
            "title":     track.get("name", ""),
            "artist":    ", ".join(a["name"] for a in track.get("artists", [])),
            "played_at": item.get("played_at", ""),
        })
    return result

def setup_interactive():
    print("\n=== Spotify Setup ===")
    print("1. Go to https://developer.spotify.com/dashboard")
    print("2. Create an app (any name)")
    print(f"3. Add redirect URI: {_REDIRECT}")
    print("4. Copy your Client ID and Client Secret\n")
    client_id     = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    with open(_CREDS_PATH, "w") as f:
        json.dump({"client_id": client_id, "client_secret": client_secret}, f, indent=2)
    params = urllib.parse.urlencode({
        "client_id": client_id, "response_type": "code",
        "redirect_uri": _REDIRECT, "scope": _SCOPE,
    })
    webbrowser.open(f"https://accounts.spotify.com/authorize?{params}")
    import http.server
    code = [None]
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            p = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in p: code[0] = p["code"][0]
            self.send_response(200); self.end_headers()
            self.wfile.write(b"<h1>JARVIS: Done. Close this tab.</h1>")
        def log_message(self, *_): pass
    print("Waiting for authorization in browser...")
    http.server.HTTPServer(("localhost", 8888), Handler).handle_request()
    if not code[0]: print("Failed."); return False
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": code[0],
        "redirect_uri": _REDIRECT,
    }).encode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token", data=data,
        headers={"Authorization": f"Basic {auth}",
                 "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=10) as r:
        token = json.loads(r.read())
    token["expires_at"] = time.time() + token.get("expires_in", 3600)
    _save_token(token)
    print("\nSpotify connected. Run 'sync spotify playlists' in JARVIS.")
    return True

if __name__ == "__main__":
    if "--setup" in sys.argv: setup_interactive()
    else: print(f"Spotify available: {is_available()}")