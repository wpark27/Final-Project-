"""Deterministic earnings-release detection from SEC EDGAR (no LLM, no API key, no bot-blocking).

For US-listed issuers (and foreign filers using 6-K) the filing list at data.sec.gov is authoritative:
  * 8-K item 2.02 ("Results of Operations") is the earnings release itself, filed the day it is published;
  * 6-K filings carry the announcement headline in `primaryDocDescription`.
Each unreported earnings event is matched one-to-one to the closest such filing, which both proves the
release happened and gives its REAL date (replacing this project's cadence guesses).
Set SEC_USER_AGENT (SEC asks for a contact in it). Fair-access limit is 10 req/s; this uses 3 in flight.
"""
from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta

import httpx

from .models import Event, Result

DEFAULT_UA = "Mozilla/5.0 (compatible; SponsorCalendarBot/1.0)"

# entity -> CIK (each verified against SEC's company_tickers.json by name, 2026-10-12)
CIKS: dict[str, int] = {
    "Blackstone": 1393818, "KKR": 1404912, "Apollo": 1858681, "Carlyle": 1527166, "Ares Management": 1176948,
    "TPG": 1880661, "Blue Owl": 1823945, "Brookfield Asset Management": 1937926, "Brookfield Corporation": 1001085,
    "Hamilton Lane": 1433642, "StepStone": 1796022, "Ares Capital (BDC)": 1287750,
    "Blue Owl Capital Corp (BDC)": 1655888, "FS KKR Capital (BDC)": 1422183, "GCM Grosvenor": 1819796,
    "Patria Investments": 1825570, "JPMorgan Chase": 19617, "Goldman Sachs": 886982, "Morgan Stanley": 895421,
    "Bank of America": 70858, "Citigroup": 831001, "Wells Fargo": 72971, "Jefferies": 96223, "Evercore": 1360901,
    "Lazard": 1311370, "PJT Partners": 1626115, "Moelis & Company": 1596967, "Houlihan Lokey": 1302215,
    "Perella Weinberg": 1777835, "Barclays": 312069, "UBS": 1610520, "Deutsche Bank": 1159508, "HSBC": 1089113,
}
DOC_HINT = re.compile(r"earnin|result|[1-4]q\d{2}|[hq][1-4]\d{2}|interim", re.I)
RESULTS_WORDS = re.compile(r"results|earnings|quarter|half[- ]year|interim|trading update|financial report", re.I)
TOLERANCE_VERIFIED = (-2, 4)      # days around a verified date in which a 2.02 counts as that release
TOLERANCE_UNVERIFIED = 35         # +/- days around a guessed date
RECENT_KINDS = ("8-K", "8-K/A", "6-K")


@dataclass
class Filing:
    cik: int
    form: str
    filed: date
    report_date: date
    items: str
    doc: str
    desc: str
    accession: str

    @property
    def base(self) -> str:
        return f"https://www.sec.gov/Archives/edgar/data/{self.cik}/{self.accession.replace('-', '')}"

    @property
    def url(self) -> str:
        return f"{self.base}/{self.doc}"

    @property
    def event_date(self) -> date:
        """8-K: the event date it reports. 6-K: the filing date (their reportDate is often the period end)."""
        return self.report_date if self.form.startswith("8-K") else self.filed

    def is_results(self) -> bool:
        if self.form.startswith("8-K"):
            return "2.02" in self.items.split(",")
        # 6-K: description is often blank/generic, so the document name ("...2q26earnin...") is checked too
        return bool(RESULTS_WORDS.search(self.desc) or DOC_HINT.search(self.doc))


def _d(s: str, fallback: date) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        return fallback


def parse_submissions(cik: int, payload: dict) -> list[Filing]:
    r = payload["filings"]["recent"]
    out = []
    for i, form in enumerate(r["form"]):
        if form not in RECENT_KINDS:
            continue
        filed = date.fromisoformat(r["filingDate"][i])
        out.append(Filing(cik, form, filed, _d(r["reportDate"][i], filed), r["items"][i] or "",
                          r["primaryDocument"][i], r["primaryDocDescription"][i] or "", r["accessionNumber"][i]))
    return out


def match(events: list[Event], filings: dict[str, list[Filing]], today: date) -> list[tuple[Event, Filing]]:
    """One-to-one matching of unreported earnings events to results filings, closest date first."""
    pairs: list[tuple[int, Event, Filing]] = []
    for ev in events:
        if ev.kind != "earnings" or ev.status == "reported" or ev.entity not in filings or ev.date > today + timedelta(days=1):
            continue
        for f in filings[ev.entity]:
            if not f.is_results() or f.filed > today:
                continue
            delta = (f.event_date - ev.date).days
            if ev.basis in ("official", "reference"):
                ok = TOLERANCE_VERIFIED[0] <= delta <= TOLERANCE_VERIFIED[1]
            else:
                ok = abs(delta) <= TOLERANCE_UNVERIFIED
            if ok:
                pairs.append((abs(delta), ev, f))
    used_e, used_f, out = set(), set(), []
    for _, ev, f in sorted(pairs, key=lambda p: (p[0], p[1].id)):
        if ev.id in used_e or f.accession in used_f:
            continue
        used_e.add(ev.id)
        used_f.add(f.accession)
        out.append((ev, f))
    return out


_HEAD = re.compile(r"[A-Z][A-Za-z&.,' \-]{2,70}?\b(?:Reports?|Announces?|Posts?)\b[^.\n]{6,200}?(?:Results|Earnings)[^.\n]{0,100}")


_DATELINE = re.compile(r"\s+(?:New York|[A-Z][a-z]+ \d{1,2}, 20\d\d|\(NYSE|\(NASDAQ)")


def headline_and_summary(text: str, f: "Filing | None", fallback: str) -> tuple[str, str]:
    """Headline + opening of an earnings release. Figures are left to the LLM enrichment step; if the headline
    can't be isolated cleanly the summary says so rather than showing navigation junk."""
    text = " ".join(text.split())
    m = _HEAD.search(text[:2500])
    if m:
        head = _DATELINE.split(m.group(0))[0].strip()           # drop "New York, April 23, 2026: ..." that follows
        return head[:220], text[m.start() + len(head):m.start() + len(head) + 420].strip()
    kind = "8-K item 2.02" if (f and f.form.startswith("8-K")) else (f.form if f else "filing")
    when = f" on {f.event_date.isoformat()}" if f else ""
    return fallback, f"Results release filed with the SEC ({kind}){when}. Open the filing for the full figures."


async def _get(c: httpx.AsyncClient, url: str):
    for attempt in range(3):
        r = await c.get(url)
        if r.status_code in (429, 503):
            await asyncio.sleep(2 * (attempt + 1))
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()


async def exhibit_text(c: httpx.AsyncClient, f: Filing) -> tuple[str, str]:
    """-> (url, text) of the press-release exhibit if the filing index names one, else the primary document."""
    from .crawler import html_to_text  # local import: crawler pulls in bs4
    url = f.url
    try:
        idx = (await _get(c, f"{f.base}/index.json")).json()["directory"]["item"]
        names = [i["name"] for i in idx if i["name"].lower().endswith((".htm", ".html"))]
        pick = next((n for n in names if re.search(r"ex[-_]?99|earnings|release|pr\d|press", n, re.I)
                     and n != f.doc and not n.endswith("_htm.xml")), None)
        if pick:
            url = f"{f.base}/{pick}"
    except (httpx.HTTPError, KeyError, ValueError):
        pass
    r = await _get(c, url)
    return url, html_to_text(r.text, url)


async def detect(events: list[Event], today: date, client: httpx.AsyncClient | None = None) -> list[tuple[Event, Filing, str, str]]:
    """Returns [(event, filing, exhibit_url, text)] for events whose release is on EDGAR."""
    ua = os.environ.get("SEC_USER_AGENT") or DEFAULT_UA
    own = client is None
    client = client or httpx.AsyncClient(headers={"User-Agent": ua}, follow_redirects=True, timeout=40)
    sem = asyncio.Semaphore(3)
    wanted = {e.entity for e in events if e.kind == "earnings" and e.status != "reported" and e.entity in CIKS}
    filings: dict[str, list[Filing]] = {}
    try:
        async def one(ent: str):
            async with sem:
                try:
                    r = await _get(client, f"https://data.sec.gov/submissions/CIK{CIKS[ent]:010d}.json")
                    filings[ent] = parse_submissions(CIKS[ent], r.json())
                except (httpx.HTTPError, KeyError, ValueError) as exc:
                    print(f"  ! edgar {ent}: {type(exc).__name__}: {exc}")
        await asyncio.gather(*(one(e) for e in sorted(wanted)))
        hits = []
        for ev, f in match(events, filings, today):
            async with sem:
                try:
                    url, text = await exhibit_text(client, f)
                except httpx.HTTPError as exc:
                    print(f"  ! edgar exhibit {ev.id}: {type(exc).__name__}")
                    url, text = f.url, ""
            hits.append((ev, f, url, text))
        return hits
    finally:
        if own:
            await client.aclose()


def apply(ev: Event, f: Filing, url: str, text: str, now: str) -> Result:
    """Mutates the event: real date, reported, official, with a result pointing at the SEC exhibit."""
    headline, summary = headline_and_summary(text, f, f"{ev.title} released")
    ev.date, ev.status, ev.basis, ev.verified_url = f.event_date, "reported", "official", url
    ev.result = Result(headline=headline, summary=summary, metrics=[], url=url, published=f.event_date, detected_at=now)
    return ev.result


TX_ITEMS = {"1.01", "2.01", "7.01", "8.01"}
NOISE = re.compile(r"shareholding|pdmr|voting rights|batch|holding\(s\) in company|transaction in own shares|director/", re.I)


async def recent_releases(ent: str, today: date, days: int = 14, client: httpx.AsyncClient | None = None,
                          limit: int = 6) -> list[tuple[str, str]]:
    """[(filing url, press-release text)] for 8-K/6-K filings in the last `days` whose items suggest a deal
    announcement (1.01 agreement, 2.01 completion, 7.01/8.01 other events). Used where an IR site is JS-only/blocked."""
    ua = os.environ.get("SEC_USER_AGENT") or DEFAULT_UA
    own = client is None
    client = client or httpx.AsyncClient(headers={"User-Agent": ua}, follow_redirects=True, timeout=40)
    try:
        r = await _get(client, f"https://data.sec.gov/submissions/CIK{CIKS[ent]:010d}.json")
        picks = []
        for f in parse_submissions(CIKS[ent], r.json()):
            if not (today - timedelta(days=days) <= f.filed <= today):
                continue
            if f.form.startswith("8-K") and not (TX_ITEMS & set(f.items.split(","))):  # 2.02-only = earnings, not a deal
                continue
            if f.form == "6-K" and NOISE.search(f.desc + " " + f.doc):
                continue
            picks.append(f)
        out = []
        for f in picks[:limit]:
            try:
                url, text = await exhibit_text(client, f)
                out.append((url, text[:6000]))
            except httpx.HTTPError:
                continue
        return out
    finally:
        if own:
            await client.aclose()
