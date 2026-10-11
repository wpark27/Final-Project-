"""Polite page fetcher restricted to an event's official domain."""
from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (compatible; SponsorCalendarBot/1.0; +https://github.com/wpark27/final-project-)"
MAX_CHARS = 24_000
_SECOND_LEVEL = {"co", "com", "org", "gov", "ac"}


def registered_domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in _SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def same_site(url: str, allowed_url: str) -> bool:
    return urlparse(url).scheme in ("http", "https") and registered_domain(url) == registered_domain(allowed_url)


def html_to_text(html: str, base_url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        tag.decompose()
    links = []
    for a in soup.find_all("a", href=True):
        label = " ".join(a.get_text(" ", strip=True).split())
        if label and len(label) > 3:
            links.append(f"- {label} -> {urljoin(base_url, a['href'])}")
    text = " ".join(soup.get_text(" ", strip=True).split())
    return (text + "\n\nLINKS:\n" + "\n".join(links[:150]))[:MAX_CHARS]


async def fetch_text(url: str, client: httpx.AsyncClient | None = None) -> str:
    own = client is None
    client = client or httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, timeout=25)
    try:
        r = await client.get(url)
        r.raise_for_status()
        ctype = r.headers.get("content-type", "")
        if "html" not in ctype and "text" not in ctype:
            return f"[non-text content: {ctype}]"
        return html_to_text(r.text, str(r.url))
    except httpx.HTTPError as e:
        return f"[fetch failed: {type(e).__name__}: {e}]"
    finally:
        if own:
            await client.aclose()
