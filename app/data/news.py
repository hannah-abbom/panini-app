"""Football news headlines from public RSS feeds (BBC, ESPN, Sky).

These are the outlets' own public RSS feeds — lightweight and intended for
syndication. Parsed with the stdlib, cached, and defensive: if a feed is
unreachable the others still show, and if all fail the UI says so. World Cup
items are floated to the top.
"""
from __future__ import annotations

from xml.etree import ElementTree as ET

import httpx

from . import cache

FEEDS = [
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ("ESPN", "https://www.espn.com/espn/rss/soccer/news"),
    ("Sky Sports", "https://www.skysports.com/rss/12040"),
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PaniniPredictor/1.0; personal use)"}
_KEYWORDS = ("world cup", "wc26", "2026", "fifa")


def _fetch_feed(name: str, url: str) -> list[dict]:
    try:
        with httpx.Client(timeout=10.0, headers=HEADERS) as client:
            resp = client.get(url)
            resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except (httpx.HTTPError, ET.ParseError, ValueError):
        return []
    items: list[dict] = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        if not title or not link:
            continue
        items.append({
            "title": title, "link": link,
            "date": (it.findtext("pubDate") or "").strip(), "source": name,
        })
        if len(items) >= 12:
            break
    return items


def get_news() -> list[dict]:
    def fetch():
        out: list[dict] = []
        for name, url in FEEDS:
            out.extend(_fetch_feed(name, url))
        return out

    items = cache.get_or_fetch("news", fetch, ttl_minutes=30) or []
    # Float World Cup-related stories to the top, keep the rest after.
    wc = [i for i in items if any(k in i["title"].lower() for k in _KEYWORDS)]
    rest = [i for i in items if i not in wc]
    return (wc + rest)[:30]
