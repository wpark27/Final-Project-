"""Builds the 2026 calendar skeleton.

Every event records HOW its date was established (`basis`), never presenting a guess as fact:
  official   - taken from the issuer / central bank / government's own published schedule or notice
  reference  - from a reputable reference calendar (NCSL, Vote411, Wikipedia) citing official sources
  estimate   - third-party aggregator estimate; issuer has not announced it
  unverified - this project's own issuer-cadence guess; the crawler replaces it with the real date

Verification pass done 2026-10-11 against the sources linked in VERIFIED_* below.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

from .models import Event, Result
from .sources import CENTRAL_BANKS, COMPANIES
from .sponsors import SPONSORS

YEAR = 2026

# entity -> [(period label, month-day)]. Dates are issuer-cadence GUESSES (basis=unverified)
# unless overridden by VERIFIED_EARNINGS below.
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
    "Brookfield Corporation": [("Q3 2026", "11-12")],
    "Onex": [("Q4 2025", "02-20"), ("Q1 2026", "05-15"), ("Q2 2026", "08-13"), ("Q3 2026", "11-06")],
    "Antin Infrastructure Partners": [("H1 2026", "09-09"), ("Q3 2026", "10-29")],
    "Tikehau Capital": [("H1 2026", "07-29"), ("Q3 2026", "10-22")],
    "Eurazeo": [("H1 2026", "07-23"), ("Q3 2026", "11-05")],
    "Wendel": [("Q1 2026", "04-23"), ("H1 2026", "07-30"), ("Q3 2026", "10-23")],
    "GCM Grosvenor": [("Q2 2026", "08-10"), ("Q3 2026", "11-04")],
    "Patria Investments": [("Q1 2026", "05-07"), ("Q2 2026", "07-31"), ("Q3 2026", "11-06")],
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

# (entity, period) -> (month-day, basis, url of the source that established it). Checked 2026-10-11.
VERIFIED_EARNINGS: dict[tuple[str, str], tuple[str, str, str]] = {
    # Company announcements
    ("Blackstone", "Q3 2026"): ("10-22", "official", "https://www.blackstone.com/?p=48748"),
    ("KKR", "Q3 2026"): ("11-09", "official", "https://secure.businesswire.com/news/home/20260929150919/en/KKR-Co.-Inc.-to-Announce-Third-Quarter-2026-Results"),
    ("Apollo", "Q3 2026"): ("11-03", "official", "https://ir.apollo.com/news-events/press-releases/detail/652/apollo-to-announce-third-quarter-2026-financial-results-on-november-3-2026"),
    ("Carlyle", "Q3 2026"): ("11-05", "official", "https://finviz.com/news/398743/carlyle-to-announce-third-quarter-2026-financial-results-and-host-investor-conference-call"),
    ("Ares Management", "Q3 2026"): ("10-29", "official", "https://finviz.com/news/396797/ares-management-corporation-schedules-earnings-release-and-conference-call-for-the-third-quarter-ending-september-30-2026"),
    ("TPG", "Q3 2026"): ("10-29", "official", "https://finviz.com/news/396426/tpg-to-announce-third-quarter-2026-financial-results-and-host-investor-call"),
    ("Blue Owl", "Q3 2026"): ("10-29", "official", "https://finviz.com/news/397615/blue-owl-capital-inc-to-announce-third-quarter-2026-results"),
    ("Blue Owl Capital Corp (BDC)", "Q3 2026"): ("11-04", "official", "https://www.placera.se/pressmeddelanden/blue-owl-capital-blue-owl-capital-corporation-schedules-earnings-release-and-quarterly-earnings-call-to-discuss-its-third-quarter-ended-september-30-2026-financial-results-20261001"),
    ("Ares Capital (BDC)", "Q3 2026"): ("10-27", "official", "https://finviz.com/news/398202/ares-capital-corporation-schedules-earnings-release-for-the-third-quarter-ended-september-30-2026"),
    ("JPMorgan Chase", "Q3 2026"): ("10-13", "official", "https://finviz.com/news/393365/jpmorganchase-to-host-third-quarter-2026-earnings-call"),
    ("Morgan Stanley", "Q3 2026"): ("10-14", "official", "https://www.morganstanley.com/about-us-ir/morgan-stanley-third-quarter-2026-investor-conference-call"),
    ("Wells Fargo", "Q3 2026"): ("10-13", "official", "https://newsroom.wf.com/news-releases/news-details/2026/Wells-Fargo-Updates-2026-Earnings-Release-Date-Information/default.aspx"),
    ("UBS", "Q3 2026"): ("10-28", "official", "https://ubs.com/calendar"),
    ("Houlihan Lokey", "FQ2 2027"): ("10-28", "official", "https://hl.com/about-us/newsroom/houlihan-lokey-announces-release-date-for-second-quarter-results-for-fiscal-year-2027/"),
    ("Hamilton Lane", "FQ2 2027"): ("11-03", "official", "https://finviz.com/news/399061/hamilton-lane-incorporated-to-announce-second-quarter-fiscal-2027-results-on-november-3-2026"),
    ("Lazard", "Q3 2026"): ("10-22", "official", "https://lazard.com/news-announcements/lazard-to-announce-third-quarter-and-nine-month-2026-financial-results/"),
    ("EQT", "Q3 2026"): ("10-15", "official", "https://www.placera.se/pressmeddelanden/eqt-invitation-to-presentation-of-eqt-abs-q3-announcement-2026-20261001"),
    ("Brookfield Corporation", "Q3 2026"): ("11-12", "official", "https://www.sec.gov/Archives/edgar/data/0001001085/000117184326006563/exh_991.htm"),
    ("Onex", "Q4 2025"): ("02-20", "official", "https://www.barchart.com/story/news/37273716/onex-to-announce-fourth-quarter-and-full-year-2025-results-on-february-20-2026"),
    ("Onex", "Q1 2026"): ("05-15", "official", "https://stocks.observer-reporter.com/observerreporter/article/gnwcq-2026-4-27-onex-to-announce-first-quarter-2026-results-on-may-15-2026"),
    ("Onex", "Q2 2026"): ("08-13", "official", "https://wwww.stockwatch.com/News/Item/Z-C!ONEX-3842940/C/ONEX"),
    ("Antin Infrastructure Partners", "H1 2026"): ("09-09", "official", "https://www.antin-ip.com/wp-content/uploads/2026/09/Antin-1H26-Results-PR-VF.pdf"),
    ("Tikehau Capital", "H1 2026"): ("07-29", "official", "https://www.tikehaucapital.com/~/media/Files/T/Tikehau-Capital-V2/documents/shareholders/publications-en/2026-07-29-tikehau-capital-h1-2026-results-presentation.pdf"),
    ("Tikehau Capital", "Q3 2026"): ("10-22", "official", "https://www.tikehaucapital.com/en/shareholders/financial-calendar"),
    ("Eurazeo", "H1 2026"): ("07-23", "official", "https://www.eurazeo.com/sites/default/files/2026-07/H1-2026-eurazeo-press_release_1.pdf"),
    ("Wendel", "Q1 2026"): ("04-23", "official", "https://www.wendelgroup.com/wp-content/uploads/2026/04/q12026-trading-update-presentation.pdf"),
    ("Wendel", "H1 2026"): ("07-30", "official", "https://mfn.se/all/a/wendel/wendel-2026-half-year-results-22a1be3d"),
    ("GCM Grosvenor", "Q2 2026"): ("08-10", "official", "https://www.gcmgrosvenor.com/2026/08/10/gcm-grosvenor-reports-second-quarter-2026-earnings-results-with-gaap-net-income-of-9-6-million-fee-related-earnings-up-21-and-adjusted-net-income-up-22-year-over-year/"),
    ("Patria Investments", "Q1 2026"): ("05-07", "official", "https://www.sec.gov/Archives/edgar/data/0001825570/000162828026031676/patriareportsfirstquarte.htm"),
    ("Patria Investments", "Q2 2026"): ("07-31", "official", "https://ir.patria.com/news-releases/news-release-details/patria-reports-second-quarter-2026-earnings-results"),
    # Third-party estimates: issuer has NOT announced these yet
    ("GCM Grosvenor", "Q3 2026"): ("11-04", "estimate", "https://unusualwhales.com/stock/GCMG/earnings"),
    ("Patria Investments", "Q3 2026"): ("11-06", "estimate", "https://beta.earningswhispers.com/go/w/PAX"),
    ("Goldman Sachs", "Q3 2026"): ("10-13", "estimate", "https://www.akrostec.com/indices/AUL500/events/2026-10-13t00-00-00z-goldman-sachs-group-inc-the-gs-financial-results-7f34f222"),
    ("Citigroup", "Q3 2026"): ("10-13", "estimate", "https://247wallst.com/cards/q3-earnings-season-front-loads-everything-into-two-mornings-unh-earnings-calendar-01m4gswtqct7fbk8xh1qmb2pkm"),
    ("Bank of America", "Q3 2026"): ("10-14", "estimate", "https://247wallst.com/cards/q3-earnings-season-front-loads-everything-into-two-mornings-unh-earnings-calendar-01m4gswtqct7fbk8xh1qmb2pkm"),
    ("Barclays", "Q3 2026"): ("10-22", "estimate", "https://www.marketscreener.com/quote/stock/BARCLAYS-PLC-9583556/calendar/"),
    ("BNP Paribas", "Q3 2026"): ("10-28", "estimate", "https://ca.marketscreener.com/quote/stock/BNP-PARIBAS-6496/calendar/"),
    ("Deutsche Bank", "Q3 2026"): ("10-28", "estimate", "https://www.opencapital.sh/stocks/db/earnings/q2-2026"),
    ("Evercore", "Q3 2026"): ("10-28", "estimate", "https://www.tipranks.com/stocks/mx:evr/earnings"),
    ("Moelis & Company", "Q3 2026"): ("10-28", "estimate", "https://beta.earningswhispers.com/go/x/MC"),
    ("StepStone", "FQ2 2027"): ("11-04", "estimate", "https://bullstory.io/en/stocks/step/earnings/2027-q2"),
    ("FS KKR Capital (BDC)", "Q3 2026"): ("11-05", "estimate", "https://beta.earningswhispers.com/go/w/FSK"),
    ("ICG", "H1 FY2027"): ("11-11", "estimate", "https://uk.marketscreener.com/quote/stock/ICG-PLC-30403106/calendar/"),
    ("Brookfield Asset Management", "Q3 2026"): ("11-04", "estimate", "https://uk.marketscreener.com/quote/stock/BROOKFIELD-ASSET-MANAGEME-147562477/calendar/"),
}

def _lpr_day(month: int) -> str:
    """20th of the month, rolled to the next weekday (public holidays are not modelled, hence 'estimate')."""
    d = date(YEAR, month, 20)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.strftime("%m-%d")


# bank -> decision dates (last day of meeting), basis per date. Checked 2026-10-11 against:
#  Fed: federalreserve.gov/monetarypolicy/fomccalendars.htm   BoE: bankofengland.co.uk/monetary-policy/upcoming-mpc-dates
#  BoJ: boj.or.jp/en/mopo/mpmsche_minu/index.htm              ECB: ecb.europa.eu/press/calendars/mgcgc (Oct, Dec; Sep 10 per ECB site)
#  BoC: bankofcanada.ca (2026 schedule, Aug 2025 notice)       RBA: rba.gov.au media release mr-25-02
#  SNB: snb.ch assessment pages / event schedule              RBI: rbi.org.in MPC schedule
RATE_DECISIONS: dict[str, list[tuple[str, str]]] = {
    "Federal Reserve (FOMC)": [(d, "official") for d in ["01-28", "03-18", "04-29", "06-17", "07-29", "09-16", "10-28", "12-09"]],
    "European Central Bank": [("02-05", "unverified"), ("03-19", "unverified"), ("04-30", "unverified"), ("06-11", "unverified"),
                              ("07-23", "unverified"), ("09-10", "official"), ("10-29", "official"), ("12-17", "official")],
    "Bank of England (MPC)": [(d, "official") for d in ["02-05", "03-19", "04-30", "06-18", "07-30", "09-17", "11-05", "12-17"]],
    "Bank of Japan": [(d, "official") for d in ["01-23", "03-19", "04-28", "06-16", "07-31", "09-18", "10-30", "12-18"]],
    "Bank of Canada": [(d, "official") for d in ["01-28", "03-18", "04-29", "06-10", "07-15", "09-02", "10-28", "12-09"]],
    "Reserve Bank of Australia": [(d, "official") for d in ["02-03", "03-17", "05-05", "06-16", "08-11", "09-29", "11-03", "12-08"]],
    "Swiss National Bank": [(d, "official") for d in ["03-19", "06-18", "09-24", "12-10"]],
    "Reserve Bank of India": [(d, "official") for d in ["02-06", "04-08", "06-05", "08-05", "10-07", "12-04"]],
    # LPR is published on the 20th (next business day if a holiday); PBoC publishes no forward calendar
    "People's Bank of China (LPR)": [(_lpr_day(m), "estimate") for m in range(1, 13)],
}

# Minutes / accounts / summaries (kind=minutes). Fed dates are the "Released" dates on the Fed's own page;
# BoJ dates are from its schedule table; SNB from its published summaries / event schedule.
MINUTES: list[tuple[str, str, str, str, str, str]] = [
    # (entity, month-day, title, basis, verified_url, note)
    ("Federal Reserve (FOMC)", "02-18", "FOMC minutes (Jan 27-28 meeting)", "official", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", ""),
    ("Federal Reserve (FOMC)", "04-08", "FOMC minutes (Mar 17-18 meeting)", "official", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", ""),
    ("Federal Reserve (FOMC)", "05-20", "FOMC minutes (Apr 28-29 meeting)", "official", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", ""),
    ("Federal Reserve (FOMC)", "07-08", "FOMC minutes (Jun 16-17 meeting)", "official", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", ""),
    ("Federal Reserve (FOMC)", "08-19", "FOMC minutes (Jul 28-29 meeting)", "official", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", ""),
    ("Federal Reserve (FOMC)", "10-07", "FOMC minutes (Sep 15-16 meeting)", "official", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", ""),
    # Fed has not yet listed these; minutes normally follow three weeks after the meeting
    ("Federal Reserve (FOMC)", "11-18", "FOMC minutes (Oct 27-28 meeting)", "estimate", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", "three weeks after meeting"),
    ("Federal Reserve (FOMC)", "12-30", "FOMC minutes (Dec 8-9 meeting)", "estimate", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", "three weeks after meeting"),
    ("Bank of Japan", "03-25", "BoJ MPM minutes (Jan 22-23 meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "05-07", "BoJ MPM minutes (Mar 18-19 meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "06-19", "BoJ MPM minutes (Apr 27-28 meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "08-05", "BoJ MPM minutes (Jun 15-16 meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "09-28", "BoJ MPM minutes (Jul 30-31 meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "11-05", "BoJ MPM minutes (Sep 17-18 meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "12-23", "BoJ MPM minutes (Oct 29-30 meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "02-02", "BoJ Summary of Opinions (Jan meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "03-30", "BoJ Summary of Opinions (Mar meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "05-12", "BoJ Summary of Opinions (Apr meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "06-24", "BoJ Summary of Opinions (Jun meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "08-10", "BoJ Summary of Opinions (Jul meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "10-01", "BoJ Summary of Opinions (Sep meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "11-10", "BoJ Summary of Opinions (Oct meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Bank of Japan", "12-28", "BoJ Summary of Opinions (Dec meeting)", "official", "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm", ""),
    ("Swiss National Bank", "04-16", "SNB summary of discussion (Mar assessment)", "official", "https://www.snb.ch/en/publications/communication/summaries/zus_20260416", ""),
    ("Swiss National Bank", "07-16", "SNB summary of discussion (Jun assessment)", "official", "https://www.snb.ch/en/publications/communication/summaries/zus_20260716", ""),
    ("Swiss National Bank", "10-22", "SNB summary of discussion (Sep assessment)", "official", "https://www.snb.ch/en/services-events/digital-services/event-schedule", ""),
]

# Political layer. (entity, kind, category, region, month-day, title, official source the crawler reads,
#                   verified_url, basis). "reference" = NCSL / Vote411 / Wikipedia, which cite official sources.
_NCSL = "https://www.ncsl.org/elections-and-campaigns/2026-state-primary-election-dates"
_V411 = "https://www.vote411.org/primaries2026"
_270 = "https://www.270towin.com/2026-state-primary-calendar/"  # independently matches Vote411 for every date below
_EU = "https://en.wikipedia.org/wiki/2026_elections_in_the_European_Union"
FEC = "https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/"
ECOM = "https://www.electoralcommission.org.uk/who-we-are-and-what-we-do/elections-and-referendums"
BWL = "https://www.bundeswahlleiterin.de/en/"
_W = "https://en.wikipedia.org/wiki/"

POLITICS: list[tuple] = [
    # US primaries and runoffs: Vote411 + 270toWin agree on every date (checked 2026-10-11)
    ("US primaries - AR, NC, TX", "election", "us_politics", "US", "03-03", "US primaries: Arkansas, North Carolina, Texas", FEC, _V411, "reference"),
    ("US primaries - MS", "election", "us_politics", "US", "03-10", "US primary: Mississippi", FEC, _V411, "reference"),
    ("US primaries - IL", "election", "us_politics", "US", "03-17", "US primary: Illinois", FEC, _V411, "reference"),
    ("US primaries - IN, OH", "election", "us_politics", "US", "05-05", "US primaries: Indiana, Ohio", FEC, _V411, "reference"),
    ("US primaries - NE, WV", "election", "us_politics", "US", "05-12", "US primaries: Nebraska, West Virginia", FEC, _V411, "reference"),
    ("US primaries - AL, GA, ID, KY, OR, PA", "election", "us_politics", "US", "05-19", "US primaries: Alabama, Georgia, Idaho, Kentucky, Oregon, Pennsylvania", FEC, _V411, "reference"),
    ("US primaries - CA, IA, MT, NM, NJ, SD", "election", "us_politics", "US", "06-02", "US primaries: California, Iowa, Montana, New Mexico, New Jersey, South Dakota", FEC, _V411, "reference"),
    ("US primaries - ME, NV, ND, SC", "election", "us_politics", "US", "06-09", "US primaries: Maine, Nevada, North Dakota, South Carolina", FEC, _V411, "reference"),
    ("US primaries - KS, MI, MO, VA, WA", "election", "us_politics", "US", "08-04", "US primaries: Kansas, Michigan, Missouri, Virginia, Washington", FEC, _V411, "reference"),
    ("US primaries - TN", "election", "us_politics", "US", "08-06", "US primary: Tennessee", FEC, _V411, "reference"),
    ("US primaries - HI", "election", "us_politics", "US", "08-08", "US primary: Hawaii", FEC, _V411, "reference"),
    ("US primaries - CT, MN, VT, WI", "election", "us_politics", "US", "08-11", "US primaries: Connecticut, Minnesota, Vermont, Wisconsin", FEC, _V411, "reference"),
    ("US primaries - AK, FL, WY", "election", "us_politics", "US", "08-18", "US primaries: Alaska, Florida, Wyoming", FEC, _V411, "reference"),
    ("US primaries - MA", "election", "us_politics", "US", "09-01", "US primary: Massachusetts", FEC, _V411, "reference"),
    ("US primaries - NH", "election", "us_politics", "US", "09-08", "US primary: New Hampshire", FEC, _V411, "reference"),
    ("US primaries - RI", "election", "us_politics", "US", "09-09", "US primary: Rhode Island", FEC, _V411, "reference"),
    ("US primaries - DE", "election", "us_politics", "US", "09-15", "US primary: Delaware", FEC, _V411, "reference"),
    ("US primaries - LA", "election", "us_politics", "US", "05-16", "US primary: Louisiana (congressional)", FEC, _270, "reference"),
    ("US primaries - DC, OK", "election", "us_politics", "US", "06-16", "US primaries: District of Columbia, Oklahoma", FEC, _270, "reference"),
    ("US primaries - MD, NY, UT", "election", "us_politics", "US", "06-23", "US primaries: Maryland, New York, Utah", FEC, _270, "reference"),
    ("US primaries - CO", "election", "us_politics", "US", "06-30", "US primary: Colorado", FEC, _270, "reference"),
    ("US primaries - AZ", "election", "us_politics", "US", "07-21", "US primary: Arizona", FEC, _270, "reference"),
    ("US runoffs - AR", "election", "us_politics", "US", "03-31", "US primary runoff: Arkansas", FEC, _270, "reference"),
    ("US runoffs - MS", "election", "us_politics", "US", "04-07", "US primary runoff: Mississippi", FEC, _270, "reference"),
    ("US runoffs - TX", "election", "us_politics", "US", "05-26", "US primary runoff: Texas", FEC, _270, "reference"),
    ("US runoffs - AL, GA", "election", "us_politics", "US", "06-16", "US primary runoffs: Alabama, Georgia", FEC, _270, "reference"),
    ("US runoffs - LA", "election", "us_politics", "US", "06-27", "US primary runoff: Louisiana", FEC, _270, "reference"),
    ("US runoffs - SD", "election", "us_politics", "US", "07-28", "US primary runoff: South Dakota", FEC, _270, "reference"),
    ("US runoffs - OK", "election", "us_politics", "US", "08-25", "US primary runoff: Oklahoma", FEC, _270, "reference"),
    ("US general runoff - GA", "election", "us_politics", "US", "12-01", "Georgia general-election runoff (if required)", FEC, _270, "reference"),
    # Federal general election: first Tuesday after the first Monday in November (2 U.S.C. 7). No presidential race in 2026.
    ("US Senate", "election", "us_politics", "US", "11-03", "US Senate elections (midterms)", FEC, _NCSL, "reference"),
    ("US House of Representatives", "election", "us_politics", "US", "11-03", "US House elections (all 435 seats, midterms)", FEC, _NCSL, "reference"),
    # UK
    ("Scottish Parliament", "election", "uk_politics", "UK", "05-07", "Scottish Parliament election", ECOM, _W + "2026_Scottish_Parliament_election", "reference"),
    ("Welsh Senedd", "election", "uk_politics", "UK", "05-07", "Senedd Cymru (Welsh Parliament) election", ECOM, _W + "2026_Senedd_election", "reference"),
    ("English local elections", "election", "uk_politics", "UK", "05-07", "English local elections", ECOM, _W + "2026_United_Kingdom_local_elections", "reference"),
    # EU institutions: Council note on 2nd-semester 2026 dates (15-16 Oct, 17-18 Dec). H1 summits not verified, omitted.
    ("European Council", "summit", "eu_politics", "Europe", "10-16", "European Council summit (Oct 15-16)", "https://www.consilium.europa.eu/en/european-council/", "https://www.consilium.europa.eu/en/meetings/future-euco-meetings/", "official"),
    ("European Council", "summit", "eu_politics", "Europe", "12-18", "European Council summit (Dec 17-18)", "https://www.consilium.europa.eu/en/european-council/", "https://www.consilium.europa.eu/en/meetings/future-euco-meetings/", "official"),
    # European national elections (Wikipedia, cites national electoral bodies)
    ("Portugal", "election", "euro_national", "Europe", "01-18", "Portugal presidential election (1st round)", "https://www.eleicoes.mai.gov.pt/", _EU, "reference"),
    ("Portugal", "election", "euro_national", "Europe", "02-08", "Portugal presidential election (runoff)", "https://www.eleicoes.mai.gov.pt/", _EU, "reference"),
    ("Germany - Baden-Wuerttemberg", "election", "euro_national", "Europe", "03-08", "Baden-Wuerttemberg state election", BWL, _W + "2026_Baden-W%C3%BCrttemberg_state_election", "reference"),
    ("France", "election", "euro_national", "Europe", "03-15", "French municipal elections (1st round)", "https://www.interieur.gouv.fr/", _W + "2026_French_municipal_elections", "reference"),
    ("France", "election", "euro_national", "Europe", "03-22", "French municipal elections (2nd round)", "https://www.interieur.gouv.fr/", _W + "2026_French_municipal_elections", "reference"),
    ("Germany - Rhineland-Palatinate", "election", "euro_national", "Europe", "03-22", "Rhineland-Palatinate state election", BWL, _W + "2026_Rhineland-Palatinate_state_election", "reference"),
    ("Slovenia", "election", "euro_national", "Europe", "03-22", "Slovenia parliamentary election", "https://www.dvk-rs.si/", _EU, "reference"),
    ("Denmark", "election", "euro_national", "Europe", "03-24", "Denmark general election", "https://valg.im.dk/", _EU, "reference"),
    ("Hungary", "election", "euro_national", "Europe", "04-12", "Hungary parliamentary election", "https://www.valasztas.hu/", _EU, "reference"),
    ("Bulgaria", "election", "euro_national", "Europe", "04-19", "Bulgaria parliamentary election", "https://www.cik.bg/en", _EU, "reference"),
    ("Cyprus", "election", "euro_national", "Europe", "05-24", "Cyprus parliamentary election", "https://www.gov.cy/moi-elections/", _EU, "reference"),
    ("Malta", "election", "euro_national", "Europe", "05-30", "Malta general election", "https://electoral.gov.mt/", _EU, "reference"),
    ("Germany - Saxony-Anhalt", "election", "euro_national", "Europe", "09-06", "Saxony-Anhalt state election", BWL, _W + "2026_Saxony-Anhalt_state_election", "reference"),
    ("Sweden", "election", "euro_national", "Europe", "09-13", "Sweden general election (Riksdag)", "https://www.val.se/", _W + "2026_Swedish_general_election", "reference"),
    ("Germany - Berlin", "election", "euro_national", "Europe", "09-20", "Berlin state election", BWL, _W + "2026_Berlin_state_election", "reference"),
    ("Germany - Mecklenburg-Vorpommern", "election", "euro_national", "Europe", "09-20", "Mecklenburg-Vorpommern state election", BWL, _W + "2026_Mecklenburg-Vorpommern_state_election", "reference"),
    ("Latvia", "election", "euro_national", "Europe", "10-03", "Latvia Saeima election", "https://www.cvk.lv/", _W + "2026_Latvian_parliamentary_election", "reference"),
    ("Bosnia and Herzegovina", "election", "euro_national", "Europe", "10-04", "Bosnia and Herzegovina general election", "https://www.izbori.ba/", _W + "2026_Bosnian_general_election", "reference"),
    ("Bulgaria", "election", "euro_national", "Europe", "10-25", "Bulgaria presidential election", "https://www.cik.bg/en", _EU, "reference"),
    ("Spain", "election", "euro_national", "Europe", "11-29", "Spain general election", "https://www.infoelectoral.interior.gob.es/", _W + "2026_Spanish_general_election", "reference"),
]

_SEEDED = "2026-10-12T00:00:00+00:00"  # when these published results/transactions were recorded from the cited sources


def _res(headline: str, summary: str, metrics: list[str], url: str, published: str) -> Result:
    return Result(headline=headline, summary=summary, metrics=metrics, url=url, published=published, detected_at=_SEEDED)


# Published results already out: only facts stated by the cited source are recorded.
RESULTS: dict[tuple[str, str], Result] = {
    ("Onex", "Q2 2026"): _res(
        "Onex Q2 2026: fee-generating AUM $43.2bn",
        "Fee-generating AUM reached about $43.2bn, up 6% year over year, helped by CLO activity in its credit business. "
        "Credit fee-generating AUM was $30.6bn versus $29.8bn at end-2025. Structured credit posted its highest-ever quarterly "
        "fee-related earnings; credit investments recorded a net loss versus a net gain a year earlier.",
        ["Fee-generating AUM $43.2bn (+6% YoY)", "Credit fee-generating AUM $30.6bn", "Structured credit FRE $19m (record)",
         "Credit investments net loss $5m vs net gain $33m a year earlier"],
        "https://alternativecreditinvestor.com/2026/08/14/onex-fee-generating-aum-hits-43-2bn-amid-active-quarter-for-clos/", "2026-08-13"),
    ("Antin Infrastructure Partners", "H1 2026"): _res(
        "Antin H1 2026: total AUM EUR33.3bn, interim dividend EUR0.28",
        "Total AUM was EUR33.3bn at 30 June 2026 (+0.8% YoY). Fee-paying AUM fell 2.9% to EUR21.2bn as Mid Cap I moved to its "
        "post-investment period. Underlying revenue fell 4.5% and underlying EBITDA fell 12.3%; the board approved an interim "
        "dividend and expects the full-year distribution to remain stable.",
        ["Total AUM EUR33.3bn", "Fee-paying AUM EUR21.2bn (-2.9%)", "Underlying revenue EUR138.5m (-4.5%)",
         "Underlying EBITDA EUR69.9m (-12.3%), 50% margin", "Interim dividend EUR0.28; FY2026 distribution expected stable at EUR0.71"],
        "https://www.antin-ip.com/wp-content/uploads/2026/09/Antin-1H26-Results-PR-VF.pdf", "2026-09-09"),
    ("Tikehau Capital", "H1 2026"): _res(
        "Tikehau Capital H1 2026: AUM EUR53.5bn, net profit EUR165m",
        "AUM reached EUR53.5bn at 30 June 2026 (+5% YoY) and fee-generating AUM rose 7% to EUR43.5bn. Net profit attributable to the "
        "group was EUR165m, double H1 2025, helped by a EUR217m gain on the sale of its Schroders stake.",
        ["AUM EUR53.5bn (+5% YoY)", "Fee-generating AUM EUR43.5bn (+7%)", "Net inflows EUR1.7bn in H1",
         "Core FRE EUR80m (+32%), 42% margin", "Net profit EUR165m"],
        "https://rankiapro.com/en/news/tikehau-capital-doubles-net-profit-to-e165-million-in-h1-2026/", "2026-07-29"),
    ("Eurazeo", "H1 2026"): _res(
        "Eurazeo H1 2026: AUM about EUR40bn, fundraising EUR2.3bn",
        "Total AUM was about EUR40bn at end-June (+9% YoY); third-party AUM EUR31.1bn (+13%). Fee-paying AUM rose 6% to EUR29.4bn "
        "and management fees were EUR213m. H1 fundraising was EUR2.3bn, with private debt raising EUR1.5bn (+73%).",
        ["Total AUM ~EUR40bn (+9%)", "Third-party AUM EUR31.1bn (+13%)", "Fee-paying AUM EUR29.4bn (+6%)",
         "Management fees EUR213m", "Dry powder EUR6.6bn (+20%)"],
        "https://www.eurazeo.com/sites/default/files/2026-07/H1-2026-eurazeo-press_release_1.pdf", "2026-07-23"),
    ("Wendel", "H1 2026"): _res(
        "Wendel H1 2026: third-party asset management at EUR48.7bn",
        "Wendel Investment Managers' third-party AuM reached EUR48.7bn (+25% over twelve months) after the Committed Advisors "
        "acquisition closed in early April. Fee-paying AuM was EUR37.8bn (+30% YoY; +11% pro forma).",
        ["WIM AuM EUR48.7bn (+25% LTM)", "Fee-paying AuM EUR37.8bn (+30% YoY, +11% pro forma)"],
        "https://mfn.se/all/a/wendel/wendel-2026-half-year-results-22a1be3d", "2026-07-30"),
    ("GCM Grosvenor", "Q2 2026"): _res(
        "GCM Grosvenor Q2 2026: AUM about $97bn, FRE up 21%",
        "AUM was about $97bn and fee-paying AUM about $78bn, both up roughly 13% YoY. Q2 fundraising was $2.3bn ($3.9bn in the "
        "first half). GAAP net income was $9.6m; fee-related earnings rose 21% and adjusted net income 22% year over year.",
        ["AUM ~$97bn (+~13%)", "Fee-paying AUM ~$78bn", "Q2 fundraising $2.3bn; H1 $3.9bn", "GAAP net income $9.6m",
         "FRE +21%; adjusted net income +22%"],
        "https://www.gcmgrosvenor.com/2026/08/10/gcm-grosvenor-reports-second-quarter-2026-earnings-results-with-gaap-net-income-of-9-6-million-fee-related-earnings-up-21-and-adjusted-net-income-up-22-year-over-year/", "2026-08-10"),
    ("Patria Investments", "Q2 2026"): _res(
        "Patria Q2 2026: fee-earning AUM $48.9bn (+32%)",
        "Fee-earning AUM ended the quarter at $48.9bn, up 32% year over year and 7% from the prior quarter. Fee-related earnings "
        "were $57.1m (+24%) at a 54.0% margin; distributable earnings were $50.7m ($0.32 per share). The firm raised $2.3bn in the "
        "quarter ($4.5bn year to date).",
        ["Fee-earning AUM $48.9bn (+32% YoY)", "FRE $57.1m (+24%), margin 54.0%", "Distributable earnings $50.7m ($0.32/share)",
         "Raised $2.3bn in Q2; $4.5bn YTD"],
        "https://ir.patria.com/news-releases/news-release-details/patria-reports-second-quarter-2026-earnings-results", "2026-07-31"),
}

# Recent transactions by sponsors above $10bn AUM, from the cited sources (checked 2026-10-12). Dates are the
# announcement/completion date the source gives; the daily scanner adds new ones from each sponsor's newsroom.
# (sponsor, month-day, title, basis, source url, summary, details)
TRANSACTIONS: list[tuple] = [
    ("Apollo", "09-29", "Apollo funds complete acquisition of Nippon Sheet Glass", "official",
     "https://www.apollo.com/insights-news/pressreleases/2026/09/apollo-funds-announce-completion-of-acquisition-of-nippon-sheet-glass-marking-new-chapter-of-growth-3371474",
     "Apollo said funds it manages completed the acquisition of Nippon Sheet Glass Co., Ltd.",
     ["Target: Nippon Sheet Glass Co., Ltd.", "Status: completed"]),
    ("Apollo", "09-15", "Apollo provides $585m financing to The Executive Centre", "official",
     "https://www.apollo.com/insights-news/pressreleases/2026/09/apollo-provides-585-million-financing-to-the-executive-centre-3362798",
     "Apollo-managed funds and others provided a $585 million financing to The Executive Centre; proceeds mainly refinance existing debt.",
     ["Borrower: The Executive Centre", "Size: $585m", "Use: refinancing"]),
    ("Blackstone", "09-21", "Blackstone agreement to acquire Flow Control reported", "reference",
     "https://www.trysignalbase.com/news/acquisitions/flow-control-acquired-by-blackstone-acquisition",
     "A deal-tracking site reported a Blackstone agreement to acquire Flow Control on September 21, 2026; financial terms were not disclosed.",
     ["Target: Flow Control", "Terms: not disclosed", "Source is a third-party tracker, not Blackstone"]),
    ("EQT", "09-04", "EQT buys majority stake in McGill and Partners from Warburg Pincus", "reference",
     "https://www.privateequitywire.co.uk/deals/3/",
     "Private Equity Wire's deal feed lists EQT buying a majority stake in McGill and Partners from Warburg Pincus for $2 billion.",
     ["Target: McGill and Partners (majority stake)", "Seller: Warburg Pincus", "Value: $2bn"]),
    ("Thoma Bravo", "08-13", "Thoma Bravo agrees to take Accelerant private", "reference",
     "https://www.insiderfinance.io/news/accelerant-take-private-with-thoma-bravo",
     "Thoma Bravo agreed to take Accelerant private at $20.25 per share, valuing the insurance marketplace at more than $4.0 billion. "
     "Thoma Bravo provided an equity commitment, so there is no financing condition; closing is expected in the first half of 2027.",
     ["Target: Accelerant", "Price: $20.25 per share", "Value: >$4.0bn", "Expected close: H1 2027"]),
    ("KKR", "08-03", "KKR to acquire Integer Holdings for $5.7bn", "reference",
     "https://app.sentisense.ai/stories/kkr-to-acquire-integer-holdings-for-5.7-billion-08032026",
     "KKR agreed to buy medical-device contract manufacturer Integer Holdings in an all-cash deal of about $5.7 billion, $127 per share; "
     "expected to close by year-end subject to regulatory approvals. The date is taken from the source's URL, not its text.",
     ["Target: Integer Holdings", "Value: ~$5.7bn, $127/share, all cash", "Expected close: year-end 2026", "Date approximate"]),
    ("Brookfield", "07-22", "Brookfield to buy AYPA Power from Blackstone in $7bn deal", "reference",
     "https://www.alternativeswatch.com/2026/07/22/brookfield-to-buy-aypa-power-from-blackstone-in-7bn-deal/",
     "AlternativesWatch reported Brookfield will buy AYPA Power from Blackstone in a $7 billion deal.",
     ["Target: AYPA Power", "Seller: Blackstone", "Value: $7bn"]),
    ("Blackstone", "07-20", "Blackstone to acquire controlling stake in Futronic", "reference",
     "https://www.akrostec.com/indices/A500PAM/events/2026-07-20t00-00-00z-blackstone-inc-bx-other-f7532bbc",
     "Blackstone announced an agreement to acquire a controlling stake in Futronic Co. for approximately $720 million.",
     ["Target: Futronic Co. (controlling stake)", "Value: ~$720m"]),
    ("Clearlake Capital", "06-09", "Clearlake completes acquisition of Pathway Capital Management", "official",
     "https://secure.businesswire.com/news/home/20260609839186/en/Clearlake-Completes-Strategic-Acquisition-of-Pathway-Capital-Management",
     "Clearlake completed its acquisition of Pathway Capital Management, which the firm says manages more than $95 billion; Clearlake cites about $185 billion of total AUM.",
     ["Target: Pathway Capital Management (> $95bn AUM)", "Status: completed"]),
    ("Apollo", "06-09", "Apollo leads $35bn financing for Broadcom AI infrastructure platform", "reference",
     "https://www.streetinsider.com/entities/Citi/APO",
     "Apollo led a $35 billion financing for Broadcom's AI infrastructure platform, alongside Blackstone and global banks.",
     ["Borrower: Broadcom AI infrastructure platform", "Size: $35bn", "Co-lenders: Blackstone, global banks"]),
    ("Stonepeak", "05-29", "Stonepeak buys majority stake in Estia Health from Bain Capital", "reference",
     "https://www.themiddlemarket.com/latest-news/stonepeak-purchases-majority-stake-in-estia-health-from-bain-capital",
     "The Middle Market reported Stonepeak purchasing a majority stake in Estia Health from Bain Capital.",
     ["Target: Estia Health (majority stake)", "Seller: Bain Capital"]),
    ("KKR", "02-05", "KKR agrees to acquire Arctos Partners", "reference",
     "https://news.bloomberglaw.com/private-equity/kkr-to-acquire-sports-investor-arctos-in-1-4-billion-deal",
     "KKR agreed to buy sports and secondaries investor Arctos Partners in a deal initially valued at $1.4 billion, plus up to $550 million in potential equity payouts, subject to regulatory and sports-league approvals.",
     ["Target: Arctos Partners", "Value: $1.4bn + up to $550m earn-out"]),
]



def _slug(s: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")


def _status(basis: str) -> str:
    return "confirmed" if basis in ("official", "reference") else "projected"


def build_events() -> list[Event]:
    out: list[Event] = []
    for entity, rows in EARNINGS.items():
        ticker, cat, region, url = COMPANIES[entity]
        for period, md in rows:
            md, basis, vurl = VERIFIED_EARNINGS.get((entity, period), (md, "unverified", None))
            res = RESULTS.get((entity, period))
            out.append(Event(id=f"{_slug(entity)}-{_slug(period)}", kind="earnings", entity=entity, ticker=ticker,
                             category=cat, region=region, date=f"{YEAR}-{md}", title=f"{entity} {period} results",
                             status="reported" if res else _status(basis), basis=basis, source_url=url,
                             verified_url=vurl, result=res))
    for bank, rows in RATE_DECISIONS.items():
        region, url = CENTRAL_BANKS[bank]
        for md, basis in rows:
            out.append(Event(id=f"{_slug(bank)}-{YEAR}-{md}", kind="rate_decision", entity=bank, category="central_bank",
                             region=region, date=f"{YEAR}-{md}", title=f"{bank} rate decision",
                             status=_status(basis), basis=basis, source_url=url,
                             verified_url=None if basis in ("unverified", "estimate") else url))
    for entity, md, title, basis, vurl, _note in MINUTES:
        region, url = CENTRAL_BANKS[entity]
        out.append(Event(id=f"{_slug(entity)}-minutes-{YEAR}-{md}", kind="minutes", entity=entity, category="central_bank",
                         region=region, date=f"{YEAR}-{md}", title=title, status=_status(basis), basis=basis,
                         source_url=url, verified_url=vurl))
    for entity, kind, cat, region, md, title, url, vurl, basis in POLITICS:
        out.append(Event(id=f"{_slug(entity)}-{YEAR}-{md}", kind=kind, entity=entity, category=cat, region=region,
                         date=f"{YEAR}-{md}", title=title, status=_status(basis), basis=basis, source_url=url,
                         verified_url=vurl))
    for sponsor, md, title, basis, vurl, summary, details in TRANSACTIONS:
        sp = SPONSORS.get(sponsor)
        out.append(Event(id=f"{_slug(sponsor)}-transaction-{_slug(title)[:50]}", kind="transaction", entity=sponsor,
                         ticker=sp["ticker"] if sp else None, category=sp["category"] if sp else "pe_sponsor",
                         region=sp["region"] if sp else "Global", date=f"{YEAR}-{md}", title=title, status="reported",
                         basis=basis, source_url=sp["news_url"] if sp else vurl, verified_url=vurl,
                         result=_res(title, summary, details, vurl, f"{YEAR}-{md}")))
    ids = [e.id for e in out]
    assert len(ids) == len(set(ids)), "duplicate event ids"
    return sorted(out, key=lambda e: (e.date, e.entity))


def atomic_write(path: Path, text: str) -> None:
    """Write via a temp file + rename so readers (the API, the browser) never see a half-written file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def write_data(path: Path, events: list[Event], updates: list[dict] | None = None, state: dict | None = None) -> None:
    payload = {
        "year": YEAR,
        "events": [json.loads(e.model_dump_json()) for e in events],
        "updates": updates or [],
        "state": state or {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=1)
    atomic_write(path, text + "\n")
    # also as a script so index.html works when opened straight from disk (file://)
    atomic_write(path.with_suffix(".js"), "window.CALENDAR_DATA = " + text + ";\n")


def write_sponsors(data_dir: Path) -> None:
    rows = [dict(name=n, **v) for n, v in SPONSORS.items()]
    text = json.dumps({"sponsors": rows}, indent=1)
    atomic_write(data_dir / "sponsors.json", text + "\n")
    atomic_write(data_dir / "sponsors.js", "window.SPONSORS_DATA = " + text + ";\n")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/events.json")
    if out.exists() and "--force" not in sys.argv:
        sys.exit(f"{out} exists; pass --force to overwrite (this discards crawler state)")
    evs = build_events()
    write_data(out, evs)
    write_sponsors(out.parent)
    print(f"wrote {len(evs)} events to {out}")
