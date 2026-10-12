"""Sponsors tracked for transaction announcements: every firm here has an AUM above $10bn.

AUM figures are what a cited source states, with its date. Where sources disagree the range is shown and
the lowest credible figure still exceeds $10bn. Nothing here is estimated by this project.
`news_url` is the firm's official newsroom/IR page that the transaction scanner reads. Listed sponsors
reuse their investor-relations press page.
"""
from __future__ import annotations

from .sources import COMPANIES

# name -> dict(listed, aum, aum_source, region, news_url, category)
_LISTED: dict[str, tuple[str, str]] = {
    # company key in sources.COMPANIES -> (aum text, source url)
    "Blackstone": ("~$1.27tn (Q4 2025, third-party ranking)", "https://www.morningstar.com/business/insights/blog/largest-alternative-asset-managers?con=20254"),
    "KKR": ("$796bn (Jun 30, 2026)", "https://www.sec.gov/Archives/edgar/data/0001404912/000140491226000022/q226earningsrelease_vf.htm"),
    "Apollo": ("$785bn-$938bn (sources vary)", "https://www.morningstar.com/business/insights/blog/largest-alternative-asset-managers?con=20254"),
    "Carlyle": ("$485bn (Jun 30, 2026)", "https://www.sec.gov/Archives/edgar/data/0001527166/000152716626000036/cg202606308-kexx992edgar.htm"),
    "Ares Management": ("~$623bn (third-party ranking)", "https://investingintheweb.com/blog/largest-alternative-asset-managers"),
    "TPG": ("~$260bn+ (third-party ranking)", "https://investingintheweb.com/blog/largest-alternative-asset-managers"),
    "Blue Owl": ("$319bn (Jun 30, 2026)", "https://ir.blueowl.com/Investors/news/news-details/2026/Blue-Owl-Capital-Inc--Second-Quarter-2026-Results/default.aspx"),
    "Brookfield Asset Management": (">$1tn (Jun 30, 2026)", "https://www.sec.gov/Archives/edgar/data/0001937926/000117184326005272/exh_991.htm"),
    "Brookfield Corporation": (">$1tn managed by BAM (Jun 30, 2026)", "https://bn.brookfield.com/sites/brookfield-bn-v2/files/Brookfield-BN-IR-V2/2026/Q2/2026-q2-bn-interim-report.pdf"),
    "EQT": ("EUR291bn (Jun 30, 2026)", "https://www.tipranks.com/news/company-announcements/eqt-ab-boosts-aum-expands-strategies-and-profits-in-first-half-of-2026"),
    "CVC Capital Partners": ("EUR153bn fee-paying (Jun 30, 2026)", "https://www.cvc.com/media/news/2026/2026-half-year-results/"),
    "Partners Group": ("$186bn (Jun 30, 2026)", "https://pulse2.com/partners-group-reaches-186-billion-in-aum-and-names-roberto-cagnati-and-juri-jenkner-co-ceos/"),
    "3i Group": ("GBP31.8bn portfolio value (Mar 31, 2026)", "https://www.3i.com/media/bc1hogm1/sp-opinion_3ig_23jul2026.pdf"),
    "ICG": ("$126bn (Mar 31, 2026)", "https://www.nasdaq.com/articles/intermediate-capital-group-h2-earnings-call-highlights"),
    "Bridgepoint": ("$97.3bn (Jun 30, 2026)", "https://www.lse.co.uk/rns/half-year-report-laps7gc97135c27.html"),
    "Hamilton Lane": ("~$146bn discretionary (Q2 2026)", "https://www.barchart.com/story/news/3636068/hamilton-lane-nasdaqhlne-beats-expectations-in-strong-q2-cy2026"),
    "StepStone": ("$245bn (Jun 30, 2026)", "https://www.kbra.com/publications/PHdZHrZV"),
    "Onex": ("$43.2bn fee-generating (Jun 30, 2026)", "https://alternativecreditinvestor.com/2026/08/14/onex-fee-generating-aum-hits-43-2bn-amid-active-quarter-for-clos/"),
    "Antin Infrastructure Partners": ("EUR33.3bn (Jun 30, 2026)", "https://www.antin-ip.com/wp-content/uploads/2026/09/Antin-1H26-Results-PR-VF.pdf"),
    "Tikehau Capital": ("EUR53.5bn (Jun 30, 2026)", "https://rankiapro.com/en/news/tikehau-capital-doubles-net-profit-to-e165-million-in-h1-2026/"),
    "Eurazeo": ("~EUR40bn (Jun 30, 2026)", "https://www.eurazeo.com/sites/default/files/2026-07/H1-2026-eurazeo-press_release_1.pdf"),
    "Wendel": ("EUR48.7bn third-party AuM (H1 2026)", "https://mfn.se/all/a/wendel/wendel-2026-half-year-results-22a1be3d"),
    "GCM Grosvenor": ("$97bn (Jun 30, 2026)", "https://www.gcmgrosvenor.com/2026/08/10/gcm-grosvenor-reports-second-quarter-2026-earnings-results-with-gaap-net-income-of-9-6-million-fee-related-earnings-up-21-and-adjusted-net-income-up-22-year-over-year/"),
    "Patria Investments": ("$48.9bn fee-earning (Jun 30, 2026)", "https://ir.patria.com/news-releases/news-release-details/patria-reports-second-quarter-2026-earnings-results"),
}

# private sponsors: name -> (region, category, aum text, aum source, newsroom url). Every URL answered HTTP 200
# when tested (2026-10-11) unless noted; the weekly healthcheck re-tests them.
_PRIVATE: dict[str, tuple[str, str, str, str, str]] = {
    "Bain Capital": ("US", "private_sponsor", "~$225bn (firm website, 2026)", "https://www.baincapital.com/", "https://www.baincapital.com/news"),
    "Thoma Bravo": ("US", "private_sponsor", "$172bn (Mar 31, 2026)", "https://altss.com/profile/thoma-bravo.md", "https://www.thomabravo.com/press-releases"),
    "Vista Equity Partners": ("US", "private_sponsor", "$103bn (Mar 31, 2026)", "https://www.vistaequitypartners.com/by-the-numbers/", "https://www.vistaequitypartners.com/insights/"),
    "Advent International": ("US", "private_sponsor", "$94bn (Mar 31, 2026)", "https://www.caproasia.com/?p=57688", "https://www.adventinternational.com/news/"),
    "Warburg Pincus": ("US", "private_sponsor", "~$105bn (2026, directory)", "https://privateequitylist.com/investors/warburg-pincus", "https://www.warburgpincus.com/news/"),
    "General Atlantic": ("US", "private_sponsor", "$123bn (Dec 31, 2025)", "https://job-boards.greenhouse.io/generalatlantic/jobs/5780173004", "https://www.generalatlantic.com/media/"),
    "Silver Lake": ("US", "private_sponsor", ">=$43bn (sources range $43-117bn)", "https://privateequitylist.com/investor/silver-lake", "https://www.silverlake.com/news/"),
    "Hellman & Friedman": ("US", "private_sponsor", "$115bn (Dec 31, 2025)", "https://altss.com/profile/hellman-friedman.md", "https://www.hf.com/news"),
    "Permira": ("Europe", "private_sponsor", "EUR75bn-90bn+ (sources vary)", "https://en.wikipedia.org/wiki/Permira", "https://www.permira.com/news-and-insights"),
    "Cinven": ("Europe", "private_sponsor", "~EUR44bn (2024)", "https://en.wikipedia.org/wiki/Cinven", "https://www.cinven.com/news-insights/"),
    "Clayton Dubilier & Rice": ("US", "private_sponsor", "$87.4bn regulatory AUM", "https://www.privatefunddata.com/fund-companies/clayton-dubilier-and-rice-llc/", "https://www.cdr.com/news"),
    "Apax Partners": ("Europe", "private_sponsor", "~$77bn (aggregators)", "https://privateequitylist.com/investors/apax-partners", "https://www.apax.com/"),
    "BC Partners": ("Europe", "private_sponsor", ">EUR40bn (firm profile, Nov 2022)", "https://boardwave.org/sponsor-profiles/bc-partners", "https://www.bcpartners.com/news"),
    "Clearlake Capital": ("US", "private_sponsor", "~$185bn (firm, Jun 2026)", "https://secure.businesswire.com/news/home/20260609839186/en/Clearlake-Completes-Strategic-Acquisition-of-Pathway-Capital-Management", "https://clearlake.com/news"),
    "Hg": ("Europe", "private_sponsor", "~$100-110bn (2026)", "https://en.wikipedia.org/wiki/Hg_(equity_firm)", "https://hgcapital.com/insights"),
    "Ardian": ("Europe", "private_sponsor", "~$200bn (2025)", "https://en.wikipedia.org/wiki/Ardian_(company)", "https://www.ardian.com/news-insights"),
    "Insight Partners": ("US", "private_sponsor", ">$90bn (Dec 31, 2025)", "https://en.wikipedia.org/wiki/Insight_Partners", "https://www.insightpartners.com/"),
    "Genstar Capital": ("US", "private_sponsor", "~$33bn", "https://en.wikipedia.org/wiki/Genstar_Capital", "https://www.gencap.com/news/"),
    "Stonepeak": ("US", "private_sponsor", "$73-93bn (2026, sources vary)", "https://en.wikipedia.org/wiki/Stonepeak", "https://stonepeak.com/news"),
    "Fortress Investment Group": ("US", "private_sponsor", "~$54bn (Mar 31, 2026)", "https://altss.com/profile/fortress-investment-group.md", "https://www.fortress.com/news"),
    "Golub Capital": ("US", "private_sponsor", ">$90bn (2026)", "https://usuaebusiness.org/resources/golub-capital/", "https://golubcapital.com/press-releases/"),
    "Cerberus": ("US", "private_sponsor", "~$65-70bn (2026)", "https://en.wikipedia.org/wiki/Cerberus_Capital_Management", "https://www.cerberus.com/news/"),
    "Sixth Street": ("US", "private_sponsor", "$135bn (Mar 31, 2026)", "https://sixthstreet.com/?p=5756", "https://sixthstreet.com/news"),
    "Leonard Green & Partners": ("US", "private_sponsor", ">$75bn (Jan 2026)", "https://www.leonardgreen.com/?p=2661", "https://www.leonardgreen.com/news"),
    "Francisco Partners": ("US", "private_sponsor", ">$25bn (firm, 2021); aggregators ~$45-50bn", "https://www.businesswire.com/news/home/20211012005772/en/Francisco-Partners-Announces-Final-Closing-of-2.2-Billion-Second-Credit-Fund", "https://www.franciscopartners.com/news"),
    "TA Associates": ("US", "private_sponsor", "~$43-65bn (aggregators)", "https://privateequitylist.com/investor/ta-associates", "https://www.ta.com/news/"),
    "Platinum Equity": ("US", "private_sponsor", "~$48bn (Dec 2024)", "https://platinumequity.com/about-us", "https://platinumequity.com/news"),
    "Centerbridge Partners": ("US", "private_sponsor", "~$44bn (firm website)", "https://www.centerbridge.com", "https://www.centerbridge.com/news"),
    "Veritas Capital": ("US", "private_sponsor", ">$54bn (Sep 2025)", "https://www.businesswire.com/news/home/20250910414578/en/Veritas-Capital-Closes-Ninth-Flagship-Fund-at-Hard-Cap-of-%2414.4-Billion", "https://www.veritascapital.com/news"),
    "Nordic Capital": ("Europe", "private_sponsor", "~EUR34bn (2025)", "https://www.altaroc.pe/en/resources/news/nordic-capital-private-equity-pioneer-in-northern-europe", "https://www.nordiccapital.com/news/"),
    "PAI Partners": ("Europe", "private_sponsor", "~EUR26bn (firm, Nov 2023)", "https://www.willkie.com/news/2023/11/willkie-advises-pai-partners-on-7-1-billion-fundraise-for-eighth-flagship-fund", "https://www.paipartners.com/news/"),
    "Hillhouse Investment": ("China", "private_sponsor", "~$100bn (2026 estimate)", "https://en.wikipedia.org/wiki/Hillhouse_Investment", "https://www.hillhouseinvestment.com/news"),
    "Adams Street Partners": ("US", "private_sponsor", "~$76bn (Jun 30, 2026)", "https://www.adamsstreetpartners.com/", "https://www.adamsstreetpartners.com/news/"),
    "HarbourVest Partners": ("US", "private_sponsor", ">$125bn (Dec 31, 2023)", "https://www.harbourvest.com/", "https://www.harbourvest.com/insights-news/"),
}


def _build() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for name, (aum, src) in _LISTED.items():
        ticker, cat, region, url = COMPANIES[name]
        out[name] = dict(listed=True, ticker=ticker, category=cat, region=region, aum=aum, aum_source=src, news_url=url)
    for name, (region, cat, aum, src, url) in _PRIVATE.items():
        out[name] = dict(listed=False, ticker=None, category=cat, region=region, aum=aum, aum_source=src, news_url=url)
    return out


SPONSORS: dict[str, dict] = _build()
