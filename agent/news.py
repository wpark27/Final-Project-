"""Running-tab headlines from Bloomberg, the Financial Times and The Economist public RSS feeds.

Only headline, link, timestamp and source are stored - never article text - and every item links out
to the publisher. Paywalled content is not fetched.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from .crawler import UA
from .sources import NEWS_FEEDS

MAX_ITEMS = 60


def parse_rss(xml_text: str, source: str) -> list[dict]:
    items = []
    root = ET.fromstring(xml_text)
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate") or ""
        if not title or not link.startswith("http"):
            continue
        try:
            ts = parsedate_to_datetime(pub).astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        items.append(dict(source=source, title=title, url=link, published=ts.isoformat(timespec="seconds")))
    return items


async def refresh(previous: list[dict] | None = None) -> list[dict]:
    got: dict[str, dict] = {i["url"]: i for i in (previous or [])}
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, timeout=30) as c:
        for source, feeds in NEWS_FEEDS.items():
            for url in feeds:
                try:
                    r = await c.get(url)
                    r.raise_for_status()
                    for it in parse_rss(r.text, source):
                        got[it["url"]] = it
                except Exception as exc:
                    print(f"  ! news {source} {url}: {type(exc).__name__}: {exc}")
    items = sorted(got.values(), key=lambda i: i["published"], reverse=True)
    return items[:MAX_ITEMS]
