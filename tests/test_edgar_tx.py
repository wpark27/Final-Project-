import asyncio
from datetime import date

import httpx
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from agent import edgar
from agent.agent import build_text_discovery_agent, discover_from_filings


def sub(rows):
    cols = ["form", "filingDate", "reportDate", "items", "primaryDocument", "primaryDocDescription", "accessionNumber"]
    return {"filings": {"recent": {c: [r[i] for r in rows] for i, c in enumerate(cols)}}}


S = sub([
    ("8-K", "2026-10-09", "2026-10-09", "1.01,9.01", "a_8k.htm", "8-K", "0001-26-000001"),     # agreement: candidate
    ("8-K", "2026-10-08", "2026-10-08", "2.02", "b_8k.htm", "8-K", "0001-26-000002"),          # earnings only: excluded
    ("8-K", "2026-08-01", "2026-08-01", "1.01", "c_8k.htm", "8-K", "0001-26-000003"),          # too old
    ("4", "2026-10-09", "", "", "f4.xml", "4", "0001-26-000004"),
])


def test_recent_releases_filters_by_items_and_age():
    def handler(req):
        u = str(req.url)
        if u.endswith("CIK0000019617.json") or "submissions" in u:
            return httpx.Response(200, json=S)
        if u.endswith("/index.json"):
            return httpx.Response(200, json={"directory": {"item": [{"name": "a_8k.htm"}, {"name": "ex99-1.htm"}]}})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<p>Blackstone agrees to acquire Acme for $1bn.</p>" * 8)
    c = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    out = asyncio.run(edgar.recent_releases("Blackstone", date(2026, 10, 12), client=c))
    assert len(out) == 1 and "ex99-1.htm" in out[0][0] and "Acme" in out[0][1]


def test_text_discovery_only_accepts_urls_it_was_given():
    good = "https://www.sec.gov/Archives/edgar/data/1/2/ex99.htm"
    m = FunctionModel(lambda msgs, info: ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"reports": [
        {"type": "transaction", "entity": "Blackstone", "title": "Real", "url": good, "published": "2026-10-09", "summary": "s", "details": ["Target: Acme"]},
        {"type": "transaction", "entity": "Blackstone", "title": "Invented URL", "url": "https://evil.example/x", "published": "2026-10-09", "summary": "s"},
        {"type": "transaction", "entity": "Blackstone", "title": "Other sec url", "url": "https://www.sec.gov/other", "published": "2026-10-09", "summary": "s"}]})]))
    res = asyncio.run(discover_from_filings(build_text_discovery_agent(m), "Blackstone", [(good, "text")], date(2026, 10, 12)))
    assert [r.title for r in res.reports] == ["Real"]
    assert asyncio.run(discover_from_filings(build_text_discovery_agent(m), "Blackstone", [], date(2026, 10, 12))).reports == []
