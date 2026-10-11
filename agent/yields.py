"""10-year government bond yields for each central bank's jurisdiction, from official data only.

No number is ever invented: if a feed fails, the previous stored value is kept (with its original
`as_of` date) and the error is recorded; banks with no free official feed are listed as unavailable.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta

import httpx

from .crawler import UA
from .sources import YIELD_UNAVAILABLE

HISTORY_DAYS = 200


def _clean(rows: list[tuple[str, float]]) -> list[tuple[str, float]]:
    return sorted({d: v for d, v in rows}.items())


async def us(c: httpx.AsyncClient, today: date):
    url = (f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/"
           f"{today.year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={today.year}&page&_format=csv")
    r = await c.get(url); r.raise_for_status()
    rows = []
    for row in csv.DictReader(io.StringIO(r.text)):
        if row.get("10 Yr"):
            rows.append((datetime.strptime(row["Date"], "%m/%d/%Y").date().isoformat(), float(row["10 Yr"])))
    return _clean(rows), "US Treasury par yield curve, 10 Yr", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates"


async def euro_area(c: httpx.AsyncClient, today: date):
    url = (f"https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y"
           f"?startPeriod={(today - timedelta(days=HISTORY_DAYS)).isoformat()}&format=csvdata")
    r = await c.get(url); r.raise_for_status()
    rows = [(x["TIME_PERIOD"], float(x["OBS_VALUE"])) for x in csv.DictReader(io.StringIO(r.text)) if x.get("OBS_VALUE")]
    return _clean(rows), "ECB euro-area AAA government bond spot yield, 10Y", "https://data.ecb.europa.eu/"


async def uk(c: httpx.AsyncClient, today: date):
    start = (today - timedelta(days=HISTORY_DAYS)).strftime("%d/%b/%Y")
    url = ("https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes"
           f"&Datefrom={start}&Dateto=now&SeriesCodes=IUDMNPY&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N")
    r = await c.get(url); r.raise_for_status()
    rows = []
    for x in csv.DictReader(io.StringIO(r.text)):
        if x.get("IUDMNPY"):
            rows.append((datetime.strptime(x["DATE"].strip(), "%d %b %Y").date().isoformat(), float(x["IUDMNPY"])))
    return _clean(rows), "Bank of England gilt 10Y nominal par yield (IUDMNPY)", "https://www.bankofengland.co.uk/boeapps/database/"


async def canada(c: httpx.AsyncClient, today: date):
    r = await c.get(f"https://www.bankofcanada.ca/valet/observations/BD.CDN.10YR.DQ.YLD/json?recent={HISTORY_DAYS}")
    r.raise_for_status()
    rows = [(o["d"], float(o["BD.CDN.10YR.DQ.YLD"]["v"])) for o in r.json()["observations"] if o["BD.CDN.10YR.DQ.YLD"].get("v")]
    return _clean(rows), "Government of Canada benchmark bond yield, 10Y", "https://www.bankofcanada.ca/rates/interest-rates/canadian-bonds/"


async def japan(c: httpx.AsyncClient, today: date):
    base = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/"
    rows = []
    for path in ("historical/jgbcme_all.csv", "jgbcme.csv"):  # full history (to month-end) + current month
        r = await c.get(base + path); r.raise_for_status()
        lines = r.text.splitlines()
        hdr = next(i for i, l in enumerate(lines) if l.startswith("Date,"))
        for x in csv.DictReader(io.StringIO("\n".join(lines[hdr:]))):
            v = (x.get("10Y") or "").strip()
            if v.replace(".", "").isdigit():
                y, m, d = x["Date"].split("/")
                rows.append((date(int(y), int(m), int(d)).isoformat(), float(v)))
    cutoff = (today - timedelta(days=HISTORY_DAYS)).isoformat()
    return _clean([r for r in rows if r[0] >= cutoff]), "Japan MoF JGB benchmark yield, 10Y", base + "index.htm"


async def australia(c: httpx.AsyncClient, today: date):
    r = await c.get("https://www.rba.gov.au/statistics/tables/csv/f2-data.csv"); r.raise_for_status()
    table = list(csv.reader(io.StringIO(r.text.lstrip("﻿"))))
    sid = next(i for i, row in enumerate(table) if row and row[0] == "Series ID")
    col = table[sid].index("FCMYGBAG10D")
    cutoff = today - timedelta(days=HISTORY_DAYS)
    rows = []
    for row in table[sid + 1:]:
        if len(row) > col and row[col] and row[0]:
            d = datetime.strptime(row[0], "%d-%b-%Y").date()
            if d >= cutoff:
                rows.append((d.isoformat(), float(row[col])))
    return _clean(rows), "RBA F2 Australian Government 10 year bond yield", "https://www.rba.gov.au/statistics/tables/#interest-rates"


# central bank -> (country label, fetcher)
FETCHERS = {
    "Federal Reserve (FOMC)": ("United States", us),
    "European Central Bank": ("Euro area", euro_area),
    "Bank of England (MPC)": ("United Kingdom", uk),
    "Bank of Japan": ("Japan", japan),
    "Bank of Canada": ("Canada", canada),
    "Reserve Bank of Australia": ("Australia", australia),
}


async def refresh(previous: dict | None, today: date | None = None) -> dict:
    today = today or date.today()
    previous = previous or {}
    out: dict[str, dict] = {}
    async with httpx.AsyncClient(headers={"User-Agent": UA}, follow_redirects=True, timeout=40) as c:
        for bank, (country, fn) in FETCHERS.items():
            old = previous.get(bank, {})
            try:
                hist, series, src = await fn(c, today)
                if not hist:
                    raise ValueError("feed returned no observations")
                (d1, v1), (d0, v0) = hist[-1], (hist[-2] if len(hist) > 1 else hist[-1])
                out[bank] = dict(country=country, series=series, source_url=src, value=v1, as_of=d1,
                                 change_1d_bp=round((v1 - v0) * 100, 1) if len(hist) > 1 else None,
                                 history=[{"d": d, "v": v} for d, v in hist[-HISTORY_DAYS:]],
                                 fetched_at=datetime.utcnow().isoformat(timespec="seconds") + "Z", error=None)
            except Exception as exc:  # keep last good value, flag staleness
                out[bank] = {**old, "country": country, "error": f"{type(exc).__name__}: {exc}"} if old else \
                    dict(country=country, series=None, value=None, as_of=None, history=[], error=f"{type(exc).__name__}: {exc}")
    for bank, why in YIELD_UNAVAILABLE.items():
        out[bank] = dict(country=None, value=None, as_of=None, history=[], unavailable=why)
    return out
