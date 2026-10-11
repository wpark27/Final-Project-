"""Official source pages the crawler is allowed to read. Edit freely: unreachable URLs are skipped."""

# entity -> (ticker, category, region, official IR / press page)
COMPANIES: dict[str, tuple[str | None, str, str, str]] = {
    # Large listed PE / alternatives sponsors
    "Blackstone": ("BX", "pe_sponsor", "US", "https://ir.blackstone.com/news/"),
    "KKR": ("KKR", "pe_sponsor", "US", "https://ir.kkr.com/news-events/press-releases/"),
    "Apollo": ("APO", "credit_sponsor", "US", "https://ir.apollo.com/news-events/press-releases"),
    "Carlyle": ("CG", "pe_sponsor", "US", "https://ir.carlyle.com/news-events/press-releases"),
    "Ares Management": ("ARES", "credit_sponsor", "US", "https://ir.aresmgmt.com/news-events/press-releases"),
    "TPG": ("TPG", "pe_sponsor", "US", "https://ir.tpg.com/news-events/press-releases"),
    "Blue Owl": ("OWL", "credit_sponsor", "US", "https://ir.blueowl.com/news-events/press-releases"),
    "Brookfield Asset Management": ("BAM", "pe_sponsor", "Canada", "https://bam.brookfield.com/press-releases"),
    "Hamilton Lane": ("HLNE", "pe_sponsor", "US", "https://ir.hamiltonlane.com/news-events/press-releases"),
    "StepStone": ("STEP", "pe_sponsor", "US", "https://ir.stepstonegroup.com/news-events/press-releases"),
    "EQT": ("EQT.ST", "pe_sponsor", "Europe", "https://eqtgroup.com/shareholders/financial-reports-presentations"),
    "CVC Capital Partners": ("CVC.AS", "pe_sponsor", "Europe", "https://www.cvc.com/investors/"),
    "Partners Group": ("PGHN.SW", "pe_sponsor", "Europe", "https://www.partnersgroup.com/en/investor-relations/"),
    "3i Group": ("III.L", "pe_sponsor", "UK", "https://www.3i.com/investors/"),
    "ICG": ("ICG.L", "credit_sponsor", "UK", "https://www.icgam.com/investors/"),
    "Bridgepoint": ("BPT.L", "pe_sponsor", "UK", "https://www.bridgepoint.eu/investors"),
    "Ares Capital (BDC)": ("ARCC", "credit_sponsor", "US", "https://www.arescapitalcorp.com/news-events/press-releases"),
    "Blue Owl Capital Corp (BDC)": ("OBDC", "credit_sponsor", "US", "https://www.blueowlcapitalcorporation.com/news-events"),
    "FS KKR Capital (BDC)": ("FSK", "credit_sponsor", "US", "https://investors.fskkr.com/news-events/press-releases"),
    # Bulge-bracket / global banks
    "JPMorgan Chase": ("JPM", "bulge_bank", "US", "https://www.jpmorganchase.com/ir/news"),
    "Goldman Sachs": ("GS", "bulge_bank", "US", "https://www.goldmansachs.com/investor-relations/financials/"),
    "Morgan Stanley": ("MS", "bulge_bank", "US", "https://www.morganstanley.com/about-us-ir/earnings-releases"),
    "Bank of America": ("BAC", "bulge_bank", "US", "https://investor.bankofamerica.com/quarterly-earnings"),
    "Citigroup": ("C", "bulge_bank", "US", "https://www.citigroup.com/global/investors/quarterly-earnings"),
    "Wells Fargo": ("WFC", "bulge_bank", "US", "https://www.wellsfargo.com/about/investor-relations/quarterly-earnings/"),
    "Barclays": ("BARC.L", "bulge_bank", "UK", "https://home.barclays/investor-relations/reports-and-events/latest-financial-results/"),
    "UBS": ("UBSG.SW", "bulge_bank", "Europe", "https://www.ubs.com/global/en/investor-relations/financial-information/quarterly-reporting.html"),
    "Deutsche Bank": ("DBK.DE", "bulge_bank", "Europe", "https://investor-relations.db.com/reports-and-events/quarterly-results/"),
    "BNP Paribas": ("BNP.PA", "bulge_bank", "Europe", "https://invest.bnpparibas/en/search/reports/documents/financial-results"),
    "HSBC": ("HSBA.L", "bulge_bank", "UK", "https://www.hsbc.com/investors/results-and-announcements"),
    "Jefferies": ("JEF", "bulge_bank", "US", "https://ir.jefferies.com/news-events/press-releases"),
    # Independent advisories (sponsor / private-capital advisory)
    "Evercore": ("EVR", "advisory", "US", "https://investors.evercore.com/news-events/press-releases"),
    "Lazard": ("LAZ", "advisory", "US", "https://www.lazard.com/investor-relations/"),
    "PJT Partners": ("PJT", "advisory", "US", "https://ir.pjtpartners.com/news-events/press-releases"),
    "Moelis & Company": ("MC", "advisory", "US", "https://investors.moelis.com/news-events/press-releases"),
    "Houlihan Lokey": ("HLI", "advisory", "US", "https://investors.hl.com/news-events/press-releases"),
    "Perella Weinberg": ("PWP", "advisory", "US", "https://investors.pwpartners.com/news-events/press-releases"),
    "Rothschild & Co": ("ROTH.PA", "advisory", "Europe", "https://www.rothschildandco.com/en/shareholders/financial-information/"),
}

CENTRAL_BANKS: dict[str, tuple[str, str]] = {
    "Federal Reserve (FOMC)": ("US", "https://www.federalreserve.gov/newsevents/pressreleases.htm"),
    "European Central Bank": ("Europe", "https://www.ecb.europa.eu/press/pr/date/html/index.en.html"),
    "Bank of England (MPC)": ("UK", "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/monetary-policy-summary-and-minutes"),
    "Bank of Japan": ("Japan", "https://www.boj.or.jp/en/mopo/mpmdeci/index.htm"),
    "Bank of Canada": ("Canada", "https://www.bankofcanada.ca/core-functions/monetary-policy/key-interest-rate/"),
    "Reserve Bank of Australia": ("Australia", "https://www.rba.gov.au/monetary-policy/int-rate-decisions/"),
    "Swiss National Bank": ("Switzerland", "https://www.snb.ch/en/the-snb/mandates-goals/monetary-policy/decisions"),
    "Reserve Bank of India": ("India", "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"),
    "People's Bank of China (LPR)": ("China", "https://www.pbc.gov.cn/en/3688006/index.html"),
}

# Pages scanned in "discover" mode for newly published market reports / outlooks
RESEARCH_PAGES: dict[str, str] = {
    "Blackstone": "https://www.blackstone.com/insights/",
    "KKR": "https://www.kkr.com/insights",
    "Apollo": "https://www.apollo.com/insights-news/insights",
    "Carlyle": "https://www.carlyle.com/global-insights",
    "Ares Management": "https://www.aresmgmt.com/news-views",
    "Brookfield": "https://www.brookfield.com/insights",
    "Blue Owl": "https://www.blueowl.com/insights",
    "Goldman Sachs": "https://www.goldmansachs.com/insights/",
    "Evercore": "https://www.evercore.com/insights/",
    "Lazard": "https://www.lazard.com/research-insights/",
    "Houlihan Lokey": "https://hl.com/insights/",
}

# Political layer: official election authorities / governments. Used for election results and
# for discovering appointments (cabinet, ministers, EU Commission leadership, confirmations).
APPOINTMENT_PAGES: dict[str, tuple[str, str, str]] = {
    # entity -> (category, region, official page)
    "US Senate (confirmations)": ("us_politics", "US", "https://www.senate.gov/legislative/nominations_new.htm"),
    "White House": ("us_politics", "US", "https://www.whitehouse.gov/presidential-actions/"),
    "UK Government": ("uk_politics", "UK", "https://www.gov.uk/search/news-and-communications?content_store_document_type=news_story&order=updated-newest"),
    "European Commission": ("eu_politics", "Europe", "https://commission.europa.eu/news-and-media/news_en"),
    "European Council / Council of the EU": ("eu_politics", "Europe", "https://www.consilium.europa.eu/en/press/press-releases/"),
    "European Parliament": ("eu_politics", "Europe", "https://www.europarl.europa.eu/news/en/press-room"),
    "France (Elysee)": ("euro_national", "Europe", "https://www.elysee.fr/en/"),
    "Germany (Federal Government)": ("euro_national", "Europe", "https://www.bundesregierung.de/breg-en"),
    "Italy (Government)": ("euro_national", "Europe", "https://www.governo.it/en"),
    "Spain (La Moncloa)": ("euro_national", "Europe", "https://www.lamoncloa.gob.es/lang/en/Paginas/index.aspx"),
}

# Central-bank leadership changes (Governor/Chair/President, deputies, board/MPC members)
LEADERSHIP_PAGES: dict[str, tuple[str, str]] = {
    "Federal Reserve": ("US", "https://www.federalreserve.gov/newsevents/pressreleases.htm"),
    "European Central Bank": ("Europe", "https://www.ecb.europa.eu/press/pr/date/html/index.en.html"),
    "Bank of England": ("UK", "https://www.bankofengland.co.uk/news"),
    "Bank of Japan": ("Japan", "https://www.boj.or.jp/en/index.htm"),
    "Bank of Canada": ("Canada", "https://www.bankofcanada.ca/press/press-releases/"),
    "Reserve Bank of Australia": ("Australia", "https://www.rba.gov.au/media-releases/"),
    "Swiss National Bank": ("Switzerland", "https://www.snb.ch/en/publications/communication/press-releases"),
    "Reserve Bank of India": ("India", "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"),
    "People's Bank of China": ("China", "https://www.pbc.gov.cn/en/3688006/index.html"),
}

# Official / UN sources for Ukraine and Middle East developments (ACLED adds event counts, see acled.py)
CONFLICT_PAGES: dict[str, str] = {
    "UN News - Europe (Ukraine)": "https://news.un.org/en/news/region/europe",
    "UN News - Middle East": "https://news.un.org/en/news/region/middle-east",
    "UN Security Council press": "https://press.un.org/en/content/security-council/meetings-coverage",
    "Institute for the Study of War": "https://understandingwar.org/research/",
}

# Running-tab headlines. Headlines + links only (no article text is stored or republished).
NEWS_FEEDS: dict[str, list[str]] = {
    "Bloomberg": [
        "https://feeds.bloomberg.com/markets/news.rss",
        "https://feeds.bloomberg.com/politics/news.rss",
    ],
    "Financial Times": [
        "https://www.ft.com/rss/home",
        "https://www.ft.com/world?format=rss",
    ],
    "The Economist": [
        "https://www.economist.com/finance-and-economics/rss.xml",
        "https://www.economist.com/the-world-this-week/rss.xml",
    ],
}

# 10-year government bond yield per central-bank jurisdiction, from official / central-bank data only.
# Banks with no free, current, official daily feed are listed with a reason instead of a made-up number.
YIELD_UNAVAILABLE: dict[str, str] = {
    "Swiss National Bank": "SNB data-portal yield cubes are not currently updated; no verified daily 10y feed.",
    "Reserve Bank of India": "No free official daily 10y feed (CCIL/FBIL are licensed).",
    "People's Bank of China (LPR)": "ChinaBond yields are not freely available via an official API.",
}
