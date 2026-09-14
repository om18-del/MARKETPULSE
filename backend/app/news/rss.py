"""RSS news ingestion via Google News (keyless, no API key needed).

Google News RSS accepts a query language/edition and topic queries and
returns publisher-attributed items — used only to *link* real articles;
sentiment is computed separately by the analyzer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

FEEDS: dict[str, list[dict[str, str]]] = {
    "global": [
        {"name": "Google News — Markets", "url": "https://news.google.com/rss/search?q=stock+markets+OR+global+markets&hl=en-US&gl=US&ceid=US:en"},
        {"name": "Google News — Economy", "url": "https://news.google.com/rss/search?q=economy+OR+inflation+OR+central+bank&hl=en-US&gl=US&ceid=US:en"},
    ],
    "india": [
        {"name": "Google News — India markets", "url": "https://news.google.com/rss/search?q=india+stock+market+OR+nifty+OR+sensex&hl=en-IN&gl=IN&ceid=IN:en"},
    ],
    "us": [
        {"name": "Google News — US markets", "url": "https://news.google.com/rss/search?q=wall+street+OR+nasdaq+OR+s%26p+500&hl=en-US&gl=US&ceid=US:en"},
    ],
    "macro": [
        {"name": "Google News — Fed & rates", "url": "https://news.google.com/rss/search?q=federal+reserve+OR+interest+rates+OR+rupee+OR+dollar&hl=en-US&gl=US&ceid=US:en"},
    ],
    "commodities": [
        {"name": "Google News — Oil & gold", "url": "https://news.google.com/rss/search?q=crude+oil+OR+gold+price&hl=en-US&gl=US&ceid=US:en"},
    ],
    "fx": [
        {"name": "Google News — Currencies", "url": "https://news.google.com/rss/search?q=currency+market+OR+dollar+OR+rupee+OR+euro&hl=en-US&gl=US&ceid=US:en"},
    ],
}

HEADERS = {"User-Agent": "MarketPulse/1.0 (educational app)"}


def _text(node) -> str:
    return "".join(node.itertext()).strip() if node is not None else ""


def parse_rss(xml: str) -> list[dict[str, Any]]:
    """Minimal namespace-tolerant RSS parser (no external feed lib)."""
    import xml.etree.ElementTree as ET

    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return items
    for item in root.iter("item"):
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        pub = _text(item.find("pubDate"))
        source = ""
        src_el = item.find("source")
        if src_el is not None:
            source = _text(src_el)
        desc = _text(item.find("description"))
        items.append({
            "title": title,
            "link": link,
            "publisher": source or (link.split("/")[2] if link and "://" in link else ""),
            "published": pub,
            "summary": desc[:300],
        })
    return items


async def fetch_topic(topic: str = "global", limit_per_feed: int = 10) -> dict[str, Any]:
    urls = FEEDS.get(topic, FEEDS["global"])
    articles: list[dict[str, Any]] = []
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=12.0, headers=HEADERS, follow_redirects=True) as http:
        for feed in urls:
            try:
                resp = await http.get(feed["url"])
                if resp.status_code != 200:
                    errors.append(f"{feed['name']}: HTTP {resp.status_code}")
                    continue
                got = parse_rss(resp.text)
                for a in got[:limit_per_feed]:
                    a["feed"] = feed["name"]
                articles.extend(got[:limit_per_feed])
            except Exception as exc:
                errors.append(f"{feed['name']}: {exc}")
    # dedupe by title
    seen: set[str] = set()
    unique = []
    for a in articles:
        key = a["title"].lower()[:80]
        if key and key not in seen:
            seen.add(key)
            unique.append(a)
    return {
        "topic": topic,
        "articles": unique[:30],
        "feeds_used": len(urls),
        "errors": errors,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
