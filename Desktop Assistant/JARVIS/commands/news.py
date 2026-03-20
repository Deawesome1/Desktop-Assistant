"""
commands/news.py — Read top news headlines by category or topic.
Uses Google News RSS — no API key required.

Say: "tech news", "sports news", "news about bitcoin", "latest news"
"""
import urllib.request
import urllib.parse
import re
from bot.speaker import speak

MAX_HEADLINES = 5

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
    """Strip CDATA wrappers, HTML tags, and source suffixes like ' - BBC News'."""
    # Unwrap CDATA
    title = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", title, flags=re.DOTALL)
    # Strip HTML tags
    title = re.sub(r"<[^>]+>", "", title)
    # Remove trailing source attribution: " - BBC News", " | Reuters"
    title = re.sub(r"\s*[-|]\s*[\w\s]{2,30}$", "", title.strip())
    return title.strip()


def _fetch_headlines(url: str) -> list[str]:
    """
    Parse only <item><title> tags — not the top-level <channel><title>.
    This avoids picking up feed/section names like 'BBC News'.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read().decode("utf-8", errors="ignore")

        # Extract only titles inside <item> blocks
        items = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)
        headlines = []
        for item in items[:MAX_HEADLINES]:
            title_match = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
            if title_match:
                title = _clean_title(title_match.group(1))
                if title:
                    headlines.append(title)

        return headlines

    except Exception as e:
        print(f"[News] Feed error: {e}")
        return []


def _search_topic(topic: str) -> list[str]:
    url = (f"https://news.google.com/rss/search"
           f"?q={urllib.parse.quote(topic)}&hl=en-US&gl=US&ceid=US:en")
    return _fetch_headlines(url)


def run(query: str) -> str:
    q = query.lower().strip()

    # Specific topic: "news about AI", "news on bitcoin"
    topic_match = re.search(
        r"(?:news about|news on|stories about|headlines about|about)\s+(.+)", q
    )
    if topic_match:
        topic = topic_match.group(1).strip()
        headlines = _search_topic(topic)
        label = f"'{topic}'"
    else:
        category = _detect_category(q)

        # Vague query — ask what category
        if category == "general":
            headlines = _fetch_headlines(CATEGORY_FEEDS["general"])
            label = "general"
        else:
            headlines = _fetch_headlines(CATEGORY_FEEDS[category])
            label = category

    if not headlines:
        speak("I couldn't fetch the news right now. Check your internet connection.")
        return "Failed: no headlines fetched"

    speak(f"Here are the top {len(headlines)} {label} headlines.")
    for i, h in enumerate(headlines, 1):
        speak(f"{i}. {h}")

    return f"Read {len(headlines)} {label} headlines."