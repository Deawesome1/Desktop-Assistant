"""
news.py — JARVIS Command
Read top news headlines by category or topic using Google News RSS.
No API key required.

Examples:
    "tech news"
    "sports news"
    "news about bitcoin"
    "latest news"
"""

import urllib.request
import urllib.parse
import re
from typing import Any, Dict, List, Optional
from brain import Brain


# ---------------------------------------------------------------------------
# Command metadata
# ---------------------------------------------------------------------------

COMMAND_NAME: str = "news"
COMMAND_ALIASES: List[str] = [
    "latest news", "news", "headlines", "top news",
    "tech news", "sports news", "business news"
]
COMMAND_DESCRIPTION: str = "Reads top news headlines by category or topic using Google News RSS."
COMMAND_OS_SUPPORT: List[str] = ["windows", "macintosh", "linux"]
COMMAND_CATEGORY: str = "information"
COMMAND_REQUIRES_INTERNET: bool = True
COMMAND_REQUIRES_ADMIN: bool = False

MAX_HEADLINES = 5


# ---------------------------------------------------------------------------
# Metadata API
# ---------------------------------------------------------------------------

def get_metadata() -> Dict[str, Any]:
    return {
        "name": COMMAND_NAME,
        "aliases": COMMAND_ALIASES,
        "description": COMMAND_DESCRIPTION,
        "os_support": COMMAND_OS_SUPPORT,
        "category": COMMAND_CATEGORY,
        "requires_internet": COMMAND_REQUIRES_INTERNET,
        "requires_admin": COMMAND_REQUIRES_ADMIN,
    }


def is_supported_on_os(os_key: str) -> bool:
    return os_key in COMMAND_OS_SUPPORT


# ---------------------------------------------------------------------------
# RSS feeds
# ---------------------------------------------------------------------------

CATEGORY_FEEDS = {
    "general":       "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "world":         "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
    "technology":    "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
    "sports":        "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en",
    "business":      "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
    "entertainment": "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en",
    "science":       "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-US&gl=US&ceid=US:en",
    "health":        "https://news.google.com/rss/headlines/section/topic/HEALTH?hl=en-US&gl=US&ceid=US:en",
    "politics":      "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-US&gl=US&ceid=US:en",
    "gaming":        "https://news.google.com/rss/search?q=gaming&hl=en-US&gl=US&ceid=US:en",
}

CATEGORY_ALIASES = {
    "tech": "technology", "finance": "business", "money": "business",
    "economy": "business", "game": "gaming", "games": "gaming",
    "esports": "gaming", "movie": "entertainment", "movies": "entertainment",
    "music": "entertainment", "celebrity": "entertainment",
    "medical": "health", "medicine": "health", "space": "science",
    "climate": "science", "government": "politics", "election": "politics",
    "congress": "politics",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_category(text: str) -> str:
    q = text.lower()
    for cat in CATEGORY_FEEDS:
        if cat in q:
            return cat
    for alias, cat in CATEGORY_ALIASES.items():
        if alias in q:
            return cat
    return "general"


def _clean_title(title: str) -> str:
    """Strip CDATA, HTML tags, and source suffixes."""
    title = re.sub(r"<!

\[CDATA

\[(.*?)\]

\]

>", r"\1", title, flags=re.DOTALL)
    title = re.sub(r"<[^>]+>", "", title)
    title = re.sub(r"\s*[-|]\s*[\w\s]{2,30}$", "", title.strip())
    return title.strip()


def _fetch_headlines(url: str) -> List[str]:
    """Fetch and parse <item><title> entries from RSS feed."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read().decode("utf-8", errors="ignore")

        items = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)
        headlines = []

        for item in items[:MAX_HEADLINES]:
            title_match = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
            if title_match:
                cleaned = _clean_title(title_match.group(1))
                if cleaned:
                    headlines.append(cleaned)

        return headlines

    except Exception:
        return []


def _search_topic(topic: str) -> List[str]:
    url = (
        "https://news.google.com/rss/search"
        f"?q={urllib.parse.quote(topic)}&hl=en-US&gl=US&ceid=US:en"
    )
    return _fetch_headlines(url)


# ---------------------------------------------------------------------------
# Public run() entrypoint
# ---------------------------------------------------------------------------

def run(
    brain: Brain,
    user_text: str,
    args: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    if args is None:
        args = []
    if context is None:
        context = {}

    os_key = brain.get_current_os_key()
    if not is_supported_on_os(os_key):
        return {
            "success": False,
            "message": f"The news command is not supported on {os_key}.",
            "data": {"os_key": os_key},
        }

    q = user_text.lower().strip()

    # ----------------------------------------------------------------------
    # Topic-based news: "news about bitcoin"
    # ----------------------------------------------------------------------
    topic_match = re.search(
        r"(?:news about|news on|stories about|headlines about|about)\s+(.+)", q
    )

    if topic_match:
        topic = topic_match.group(1).strip()
        headlines = _search_topic(topic)
        label = f"'{topic}'"
    else:
        category = _detect_category(q)
        label = category
        headlines = _fetch_headlines(CATEGORY_FEEDS.get(category, CATEGORY_FEEDS["general"]))

    # ----------------------------------------------------------------------
    # No headlines
    # ----------------------------------------------------------------------
    if not headlines:
        brain.event("user_confused")
        return {
            "success": False,
            "message": "I couldn't fetch the news right now. Check your internet connection.",
            "data": {"category_or_topic": label},
        }

    # ----------------------------------------------------------------------
    # Success
    # ----------------------------------------------------------------------
    brain.event("task_success")
    brain.remember("news_queries", f"{label}: {len(headlines)} headlines")

    return {
        "success": True,
        "message": f"Here are the top {len(headlines)} {label} headlines.",
        "data": {
            "label": label,
            "headlines": headlines,
            "count": len(headlines),
        },
    }
