"""ACLED conflict-event counts for Ukraine and the Middle East (needs free ACLED credentials).

Set ACLED_EMAIL and ACLED_PASSWORD. Uses ACLED's OAuth password grant and /api/acled/read as documented at
https://acleddata.com/api-documentation/getting-started . Without credentials this returns a clear
'not configured' marker instead of any data.
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import date, timedelta

import httpx

THEATRES = {
    "Ukraine war": ["Ukraine", "Russia"],
    "Middle East": ["Israel", "Palestine", "Lebanon", "Syria", "Iran", "Yemen", "Iraq"],
}
WINDOW_DAYS = 7
PAGE_SIZE = 5000
MAX_PAGES = 20


async def _token(c: httpx.AsyncClient) -> str:
    r = await c.post("https://acleddata.com/oauth/token", data={
        "username": os.environ["ACLED_EMAIL"], "password": os.environ["ACLED_PASSWORD"],
        "grant_type": "password", "client_id": "acled", "scope": "authenticated"})
    r.raise_for_status()
    return r.json()["access_token"]


def summarise(rows: list[dict]) -> dict:
    by_country: dict[str, dict] = defaultdict(lambda: {"events": 0, "fatalities": 0})
    by_type: dict[str, int] = defaultdict(int)
    for x in rows:
        c = by_country[x["country"]]
        c["events"] += 1
        c["fatalities"] += int(x.get("fatalities") or 0)
        by_type[x["event_type"]] += 1
    return dict(events=len(rows), fatalities=sum(v["fatalities"] for v in by_country.values()),
                by_country=dict(by_country), by_event_type=dict(by_type))


async def refresh(today: date | None = None) -> dict:
    if not (os.environ.get("ACLED_EMAIL") and os.environ.get("ACLED_PASSWORD")):
        return {"status": "not_configured",
                "note": "Set ACLED_EMAIL / ACLED_PASSWORD (free ACLED account) to enable conflict event counts."}
    today = today or date.today()
    start = today - timedelta(days=WINDOW_DAYS)
    out: dict = {"status": "ok", "source": "ACLED (acleddata.com)", "window": [start.isoformat(), today.isoformat()],
                 "theatres": {}}
    async with httpx.AsyncClient(timeout=90) as c:
        headers = {"Authorization": f"Bearer {await _token(c)}"}
        for name, countries in THEATRES.items():
            q = ":OR:".join(f"country={x}" for x in countries)
            rows: list[dict] = []
            for page in range(1, MAX_PAGES + 1):  # API caps a call at 5000 rows; paginate with &page=N
                url = (f"https://acleddata.com/api/acled/read?_format=json&{q}&event_date={start}|{today}"
                       f"&event_date_where=BETWEEN&fields=event_date|event_type|country|fatalities"
                       f"&limit={PAGE_SIZE}&page={page}")
                r = await c.get(url, headers=headers)
                r.raise_for_status()
                body = r.json()
                if body.get("status") != 200:
                    raise RuntimeError(f"ACLED returned status {body.get('status')}")
                rows += body["data"]
                if len(body["data"]) < PAGE_SIZE:
                    break
            else:
                out.setdefault("truncated", []).append(name)  # hit MAX_PAGES: counts are a lower bound
            out["theatres"][name] = summarise(rows)
    return out
