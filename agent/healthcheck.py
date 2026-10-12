"""Check that every configured official source URL is reachable.

  python -m agent.healthcheck            # table of failures
  python -m agent.healthcheck --all      # every URL

A source that fails here is skipped (not guessed at) by the crawler. 403s are often bot-blocks that only
affect some networks, so a 403 is reported separately from 404/5xx (genuinely wrong or down).
"""
from __future__ import annotations

import asyncio
import sys

import httpx

from . import sources
from .crawler import UA


def all_urls() -> dict[str, str]:
    out: dict[str, str] = {}
    for name, (_t, _c, _r, url) in sources.COMPANIES.items():
        out[f"company:{name}"] = url
    for name, (_r, url) in sources.CENTRAL_BANKS.items():
        out[f"central_bank:{name}"] = url
    for name, url in sources.RESEARCH_PAGES.items():
        out[f"research:{name}"] = url
    for name, (_c, _r, url) in sources.APPOINTMENT_PAGES.items():
        out[f"politics:{name}"] = url
    for name, (_r, url) in sources.LEADERSHIP_PAGES.items():
        out[f"leadership:{name}"] = url
    for name, url in sources.CONFLICT_PAGES.items():
        out[f"conflict:{name}"] = url
    from .sponsors import SPONSORS
    for name, sp in SPONSORS.items():
        out[f"deals:{name}"] = sp["news_url"]
    return out


async def check(urls: dict[str, str]) -> dict[str, str]:
    sem = asyncio.Semaphore(3)  # gentle: many sites answer 403/429 to bursts
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, timeout=25) as c:
        async def one(k, u):
            async with sem:
                for attempt in range(2):  # one retry after a pause for 403/429 (rate limiting)
                    try:
                        r = await c.get(u)
                    except httpx.HTTPError as e:
                        return k, type(e).__name__
                    if r.status_code not in (403, 429) or attempt:
                        return k, str(r.status_code)
                    await asyncio.sleep(3)
                return k, "403"
        return dict(await asyncio.gather(*(one(k, u) for k, u in urls.items())))


def main() -> int:
    urls = all_urls()
    res = asyncio.run(check(urls))
    bad = {k: v for k, v in res.items() if v != "200"}
    for k, v in sorted(res.items(), key=lambda kv: kv[1]):
        if "--all" in sys.argv or v != "200":
            print(f"{v:>14}  {k}  {urls[k]}")
    print(f"\n{len(urls) - len(bad)}/{len(urls)} reachable")
    return 1 if any(v not in ("200", "403") for v in res.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
