"""Builds the 2026 calendar skeleton. Every date here is PROJECTED (issuer pattern / published
central-bank calendars) until the crawler confirms it from an official source."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .models import Event
from .sources import CENTRAL_BANKS, COMPANIES

YEAR = 2026

# entity -> [(period label, month-day)] ; typical issuer cadence, to be confirmed by the crawler
EARNINGS: dict[str, list[tuple[str, str]]] = {
    "Blackstone": [("Q4 2025", "01-29"), ("Q1 2026", "04-16"), ("Q2 2026", "07-23"), ("Q3 2026", "10-22")],
    "KKR": [("Q4 2025", "02-03"), ("Q1 2026", "05-05"), ("Q2 2026", "08-04"), ("Q3 2026", "11-03")],
    "Apollo": [("Q4 2025", "02-04"), ("Q1 2026", "05-05"), ("Q2 2026", "08-04"), ("Q3 2026", "11-04")],
    "Carlyle": [("Q4 2025", "02-05"), ("Q1 2026", "04-30"), ("Q2 2026", "07-30"), ("Q3 2026", "11-05")],
    "Ares Management": [("Q4 2025", "02-06"), ("Q1 2026", "05-01"), ("Q2 2026", "07-31"), ("Q3 2026", "10-30")],
    "TPG": [("Q4 2025", "02-12"), ("Q1 2026", "05-07"), ("Q2 2026", "08-06"), ("Q3 2026", "11-05")],
    "Blue Owl": [("Q4 2025", "02-05"), ("Q1 2026", "05-07"), ("Q2 2026", "08-06"), ("Q3 2026", "11-05")],
    "Brookfield Asset Management": [("Q4 2025", "02-12"), ("Q1 2026", "05-07"), ("Q2 2026", "08-06"), ("Q3 2026", "11-06")],
    "Hamilton Lane": [("FQ3 2026", "02-05"), ("FQ4 2026", "05-21"), ("FQ1 2027", "08-06"), ("FQ2 2027", "11-05")],
    "StepStone": [("FQ3 2026", "02-11"), ("FQ4 2026", "05-21"), ("FQ1 2027", "08-06"), ("FQ2 2027", "11-05")],
    "EQT": [("Q4 2025", "01-29"), ("Q1 2026", "04-23"), ("Q2 2026", "07-16"), ("Q3 2026", "10-22")],
    "CVC Capital Partners": [("FY 2025", "03-04"), ("H1 2026", "09-09")],
    "Partners Group": [("AuM 2025", "01-14"), ("FY 2025", "03-11"), ("AuM H1 2026", "07-14"), ("H1 2026", "09-09")],
    "3i Group": [("FY 2026 (Mar)", "05-21"), ("H1 FY2027", "11-12")],
    "ICG": [("FY 2026 (Mar)", "05-20"), ("H1 FY2027", "11-10")],
    "Bridgepoint": [("FY 2025", "03-17"), ("H1 2026", "09-17")],
    "Ares Capital (BDC)": [("Q4 2025", "02-04"), ("Q1 2026", "04-29"), ("Q2 2026", "07-29"), ("Q3 2026", "10-28")],
    "Blue Owl Capital Corp (BDC)": [("Q4 2025", "02-18"), ("Q1 2026", "05-06"), ("Q2 2026", "08-05"), ("Q3 2026", "11-05")],
    "FS KKR Capital (BDC)": [("Q4 2025", "02-25"), ("Q1 2026", "05-06"), ("Q2 2026", "08-05"), ("Q3 2026", "11-05")],
    "JPMorgan Chase": [("Q4 2025", "01-13"), ("Q1 2026", "04-14"), ("Q2 2026", "07-14"), ("Q3 2026", "10-14")],
    "Goldman Sachs": [("Q4 2025", "01-15"), ("Q1 2026", "04-13"), ("Q2 2026", "07-14"), ("Q3 2026", "10-14")],
    "Morgan Stanley": [("Q4 2025", "01-15"), ("Q1 2026", "04-15"), ("Q2 2026", "07-15"), ("Q3 2026", "10-15")],
    "Bank of America": [("Q4 2025", "01-14"), ("Q1 2026", "04-15"), ("Q2 2026", "07-15"), ("Q3 2026", "10-15")],
    "Citigroup": [("Q4 2025", "01-14"), ("Q1 2026", "04-14"), ("Q2 2026", "07-14"), ("Q3 2026", "10-14")],
    "Wells Fargo": [("Q4 2025", "01-14"), ("Q1 2026", "04-14"), ("Q2 2026", "07-14"), ("Q3 2026", "10-14")],
    "Barclays": [("FY 2025", "02-10"), ("Q1 2026", "04-28"), ("H1 2026", "07-29"), ("Q3 2026", "10-28")],
    "UBS": [("Q4 2025", "02-03"), ("Q1 2026", "04-29"), ("Q2 2026", "07-29"), ("Q3 2026", "10-29")],
    "Deutsche Bank": [("Q4 2025", "01-29"), ("Q1 2026", "04-29"), ("Q2 2026", "07-22"), ("Q3 2026", "10-28")],
    "BNP Paribas": [("Q4 2025", "02-05"), ("Q1 2026", "04-23"), ("Q2 2026", "07-23"), ("Q3 2026", "10-22")],
    "HSBC": [("FY 2025", "02-25"), ("Q1 2026", "04-28"), ("H1 2026", "07-28"), ("Q3 2026", "10-27")],
    "Jefferies": [("FQ4 2025", "01-28"), ("FQ1 2026", "03-25"), ("FQ2 2026", "06-24"), ("FQ3 2026", "09-23")],
    "Evercore": [("Q4 2025", "01-29"), ("Q1 2026", "04-21"), ("Q2 2026", "07-22"), ("Q3 2026", "10-21")],
    "Lazard": [("Q4 2025", "01-29"), ("Q1 2026", "04-28"), ("Q2 2026", "07-28"), ("Q3 2026", "10-28")],
    "PJT Partners": [("Q4 2025", "01-28"), ("Q1 2026", "04-23"), ("Q2 2026", "07-23"), ("Q3 2026", "10-22")],
    "Moelis & Company": [("Q4 2025", "02-04"), ("Q1 2026", "04-22"), ("Q2 2026", "07-22"), ("Q3 2026", "10-21")],
    "Houlihan Lokey": [("FQ3 2026", "01-29"), ("FQ4 2026", "05-21"), ("FQ1 2027", "07-30"), ("FQ2 2027", "10-29")],
    "Perella Weinberg": [("Q4 2025", "02-05"), ("Q1 2026", "05-06"), ("Q2 2026", "08-05"), ("Q3 2026", "11-04")],
    "Rothschild & Co": [("FY 2025", "03-12"), ("H1 2026", "09-24")],
}

# bank -> list of decision dates (last day of meeting). From each bank's published 2026 calendar.
RATE_DECISIONS: dict[str, list[str]] = {
    "Federal Reserve (FOMC)": ["01-28", "03-18", "04-29", "06-17", "07-29", "09-16", "10-28", "12-09"],
    "European Central Bank": ["02-05", "03-19", "04-30", "06-11", "07-23", "09-10", "10-29", "12-17"],
    "Bank of England (MPC)": ["02-05", "03-19", "04-30", "06-18", "07-30", "09-17", "11-05", "12-17"],
    "Bank of Japan": ["01-23", "03-19", "04-28", "06-16", "07-31", "09-18", "10-30", "12-18"],
    "Bank of Canada": ["01-28", "03-11", "04-15", "06-03", "07-15", "09-02", "10-28", "12-09"],
    "Reserve Bank of Australia": ["02-03", "03-17", "05-05", "06-16", "08-11", "09-29", "11-03", "12-08"],
    "Swiss National Bank": ["03-19", "06-18", "09-24", "12-10"],
    "Reserve Bank of India": ["02-06", "04-08", "06-05", "08-06", "10-07", "12-04"],
    "People's Bank of China (LPR)": [f"{m:02d}-20" for m in range(1, 13)],
}

# Political layer: (entity, kind, category, region, date, title, official source). All PROJECTED until confirmed.
FEC = "https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/"
ECOM = "https://www.electoralcommission.org.uk/who-we-are-and-what-we-do/elections-and-referendums"
ECS = "https://www.consilium.europa.eu/en/european-council/"
POLITICS = [
    ("US primaries - TX, NC, AR", "election", "us_politics", "US", "03-03", "US primaries: Texas, North Carolina, Arkansas", FEC),
    ("US primaries - IL", "election", "us_politics", "US", "03-17", "US primary: Illinois", FEC),
    ("US primaries - IN, OH", "election", "us_politics", "US", "05-05", "US primaries: Indiana, Ohio", FEC),
    ("US primaries - NE, WV", "election", "us_politics", "US", "05-12", "US primaries: Nebraska, West Virginia", FEC),
    ("US primaries - PA, GA, KY, ID, OR", "election", "us_politics", "US", "05-19", "US primaries: Pennsylvania, Georgia, Kentucky, Idaho, Oregon", FEC),
    ("US primaries - CA, NJ, IA, MT, NM, SD", "election", "us_politics", "US", "06-02", "US primaries: California, New Jersey, Iowa, Montana, New Mexico, South Dakota", FEC),
    ("US primaries - NY, UT, OK", "election", "us_politics", "US", "06-23", "US primaries: New York, Utah, Oklahoma", FEC),
    ("US primaries - CO", "election", "us_politics", "US", "06-30", "US primary: Colorado", FEC),
    ("US primaries - MI, MO, KS, WA, AZ", "election", "us_politics", "US", "08-04", "US primaries: Michigan, Missouri, Kansas, Washington, Arizona", FEC),
    ("US primaries - MN, WI, CT, VT", "election", "us_politics", "US", "08-11", "US primaries: Minnesota, Wisconsin, Connecticut, Vermont", FEC),
    ("US primaries - FL, AK, WY", "election", "us_politics", "US", "08-18", "US primaries: Florida, Alaska, Wyoming", FEC),
    ("US primaries - MA", "election", "us_politics", "US", "09-01", "US primary: Massachusetts", FEC),
    ("US primaries - NH, DE, RI", "election", "us_politics", "US", "09-15", "US primaries: New Hampshire, Delaware, Rhode Island", FEC),
    ("US Senate", "election", "us_politics", "US", "11-03", "US Senate elections (35 seats incl. specials) - midterms", FEC),
    ("US House of Representatives", "election", "us_politics", "US", "11-03", "US House elections (all 435 seats) - midterms", FEC),
    ("US Senate runoffs", "election", "us_politics", "US", "12-01", "Georgia general-election runoff (if required)", FEC),
    ("Scottish Parliament", "election", "uk_politics", "UK", "05-07", "Scottish Parliament election", ECOM),
    ("Welsh Senedd", "election", "uk_politics", "UK", "05-07", "Senedd Cymru (Welsh Parliament) election", ECOM),
    ("English local elections", "election", "uk_politics", "UK", "05-07", "English local elections", ECOM),
    ("European Council", "summit", "eu_politics", "Europe", "03-20", "European Council summit (Mar)", ECS),
    ("European Council", "summit", "eu_politics", "Europe", "06-26", "European Council summit (Jun)", ECS),
    ("European Council", "summit", "eu_politics", "Europe", "10-23", "European Council summit (Oct)", ECS),
    ("European Council", "summit", "eu_politics", "Europe", "12-18", "European Council summit (Dec)", ECS),
    ("Portugal", "election", "euro_national", "Europe", "01-18", "Portugal presidential election (1st round)", "https://www.eleicoes.mai.gov.pt/"),
    ("Germany - Baden-Wuerttemberg", "election", "euro_national", "Europe", "03-08", "Baden-Wuerttemberg state election", "https://www.bundeswahlleiterin.de/en/"),
    ("France", "election", "euro_national", "Europe", "03-22", "French municipal elections (2nd round)", "https://www.interieur.gouv.fr/"),
    ("Germany - Rhineland-Palatinate", "election", "euro_national", "Europe", "03-22", "Rhineland-Palatinate state election", "https://www.bundeswahlleiterin.de/en/"),
    ("Slovenia", "election", "euro_national", "Europe", "03-22", "Slovenia parliamentary election", "https://www.dvk-rs.si/"),
    ("Hungary", "election", "euro_national", "Europe", "04-12", "Hungary parliamentary election", "https://www.valasztas.hu/"),
    ("Cyprus", "election", "euro_national", "Europe", "05-24", "Cyprus parliamentary election", "https://www.elections.gov.cy/"),
    ("Germany - Saxony-Anhalt", "election", "euro_national", "Europe", "09-06", "Saxony-Anhalt state election", "https://www.bundeswahlleiterin.de/en/"),
    ("Sweden", "election", "euro_national", "Europe", "09-13", "Sweden general election (Riksdag)", "https://www.val.se/"),
    ("Germany - Berlin / Mecklenburg-Vorpommern", "election", "euro_national", "Europe", "09-20", "Berlin and Mecklenburg-Vorpommern state elections", "https://www.bundeswahlleiterin.de/en/"),
    ("Latvia", "election", "euro_national", "Europe", "10-03", "Latvia Saeima election", "https://www.cvk.lv/en"),
    ("Bosnia and Herzegovina", "election", "euro_national", "Europe", "10-04", "Bosnia and Herzegovina general election", "https://www.izbori.ba/"),
    ("Denmark", "election", "euro_national", "Europe", "10-31", "Denmark general election (must be held by this date)", "https://valg.im.dk/"),
    ("Bulgaria", "election", "euro_national", "Europe", "11-08", "Bulgaria presidential election (est.)", "https://www.cik.bg/en"),
]


def _slug(s: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")


def build_events() -> list[Event]:
    out: list[Event] = []
    for entity, rows in EARNINGS.items():
        ticker, cat, region, url = COMPANIES[entity]
        for period, md in rows:
            out.append(
                Event(
                    id=f"{_slug(entity)}-{_slug(period)}",
                    kind="earnings",
                    entity=entity,
                    ticker=ticker,
                    category=cat,
                    region=region,
                    date=f"{YEAR}-{md}",
                    title=f"{entity} {period} results",
                    source_url=url,
                )
            )
    for bank, dates in RATE_DECISIONS.items():
        region, url = CENTRAL_BANKS[bank]
        for md in dates:
            out.append(
                Event(
                    id=f"{_slug(bank)}-{YEAR}-{md}",
                    kind="rate_decision",
                    entity=bank,
                    category="central_bank",
                    region=region,
                    date=f"{YEAR}-{md}",
                    title=f"{bank} rate decision",
                    source_url=url,
                )
            )
    for entity, kind, cat, region, md, title, url in POLITICS:
        out.append(Event(id=f"{_slug(entity)}-{YEAR}-{md}", kind=kind, entity=entity, category=cat,
                         region=region, date=f"{YEAR}-{md}", title=title, source_url=url))
    return sorted(out, key=lambda e: (e.date, e.entity))


def write_data(path: Path, events: list[Event], updates: list[dict] | None = None) -> None:
    payload = {
        "year": YEAR,
        "generated": None,
        "events": [json.loads(e.model_dump_json()) for e in events],
        "updates": updates or [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=1)
    path.write_text(text + "\n")
    # also as a script so index.html works when opened straight from disk (file://)
    path.with_suffix(".js").write_text("window.CALENDAR_DATA = " + text + ";\n")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/events.json")
    if out.exists() and "--force" not in sys.argv:
        sys.exit(f"{out} exists; pass --force to overwrite (this discards crawler state)")
    evs = build_events()
    write_data(out, evs)
    print(f"wrote {len(evs)} events to {out}")
