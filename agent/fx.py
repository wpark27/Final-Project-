"""Currency exchange rates from the ECB euro foreign exchange reference rates (official, free, no key).

The ECB publishes one fixing per working day (~16:00 CET), so these are daily reference rates, not live
quotes. Every pair is a cross computed from the ECB's EUR-based rates. No rate is ever invented: on a
failed fetch the previous stored rates are kept and flagged stale.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx

from .crawler import UA

DAILY = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
HIST = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
SOURCE_PAGE = "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html"

# (base, quote): rate = how many QUOTE per 1 BASE, market-convention ordering
PAIRS: list[tuple[str, str]] = [
    ("EUR", "USD"), ("GBP", "USD"), ("USD", "JPY"), ("USD", "CHF"), ("USD", "CAD"), ("AUD", "USD"),
    ("USD", "CNY"), ("USD", "INR"), ("EUR", "GBP"), ("EUR", "JPY"), ("EUR", "CHF"), ("USD", "SEK"),
]
_NS = {"e": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}


def parse_ecb(xml_text: str) -> dict[str, dict[str, float]]:
    """-> {date: {currency: units per EUR}} (EUR itself = 1.0)."""
    root = ET.fromstring(xml_text)
    out: dict[str, dict[str, float]] = {}
    for day in root.iterfind(".//e:Cube[@time]", _NS):
        rates = {c.get("currency"): float(c.get("rate")) for c in day.iterfind("e:Cube", _NS)}
        rates["EUR"] = 1.0
        out[day.get("time")] = rates
    return out


def cross(rates: dict[str, float], base: str, quote: str) -> float | None:
    if base not in rates or quote not in rates:
        return None
    return rates[quote] / rates[base]


def build(days: dict[str, dict[str, float]]) -> dict:
    dates = sorted(days)
    if not dates:
        raise ValueError("ECB feed contained no rates")
    last, prev = dates[-1], (dates[-2] if len(dates) > 1 else None)
    pairs = []
    for base, quote in PAIRS:
        v = cross(days[last], base, quote)
        if v is None:
            continue  # currency not in ECB set today: omit rather than guess
        p = cross(days[prev], base, quote) if prev else None
        hist = [{"d": d, "v": round(x, 6)} for d in dates if (x := cross(days[d], base, quote)) is not None]
        pairs.append(dict(pair=f"{base}/{quote}", base=base, quote=quote, rate=round(v, 6),
                          change_pct=round((v / p - 1) * 100, 2) if p else None, history=hist))
    return dict(as_of=last, source="ECB euro foreign exchange reference rates", source_url=SOURCE_PAGE,
                fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), error=None, pairs=pairs)


async def refresh(previous: dict | None = None) -> dict:
    try:
        async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, timeout=40) as c:
            r = await c.get(HIST)
            r.raise_for_status()
            return build(parse_ecb(r.text))
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        return {**previous, "error": err} if previous else dict(as_of=None, source_url=SOURCE_PAGE, pairs=[], error=err)
