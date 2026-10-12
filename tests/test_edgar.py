import asyncio
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import httpx
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from agent import edgar, run
from agent.models import Event
from agent.seed import build_events, write_data


def sub(rows):
    cols = ["form", "filingDate", "reportDate", "items", "primaryDocument", "primaryDocDescription", "accessionNumber"]
    return {"filings": {"recent": {c: [r[i] for r in rows] for i, c in enumerate(cols)}}}


KKR = sub([
    ("8-K", "2026-07-30", "2026-07-30", "2.02,9.01", "kkr-20260730.htm", "8-K", "0001404912-26-000022"),
    ("8-K", "2026-07-31", "2026-07-30", "1.01,2.03", "x_8k.htm", "8-K", "0001140361-26-030498"),   # not results
    ("8-K", "2026-05-05", "2026-05-05", "2.02", "kkr-20260505.htm", "8-K", "0001404912-26-000011"),
    ("4", "2026-08-01", "", "", "f4.xml", "4", "0001-26-1"),
])


def ev(id_, ent, d, basis="unverified", kind="earnings"):
    return Event(id=id_, kind=kind, entity=ent, category="pe_sponsor", region="US", date=d, title=f"{ent} {id_}",
                 basis=basis, source_url="https://ir.kkr.com/", status="projected" if basis == "unverified" else "confirmed")


def test_parse_keeps_only_8k_6k():
    fs = edgar.parse_submissions(1404912, KKR)
    assert [f.form for f in fs] == ["8-K", "8-K", "8-K"] and sum(f.is_results() for f in fs) == 2


def test_match_replaces_guess_with_real_date_one_to_one():
    fs = {"KKR": edgar.parse_submissions(1404912, KKR)}
    q1, q2 = ev("q1", "KKR", date(2026, 5, 7)), ev("q2", "KKR", date(2026, 8, 4))     # both guesses are off
    out = {e.id: f.report_date for e, f in edgar.match([q1, q2], fs, date(2026, 10, 12))}
    assert out == {"q1": date(2026, 5, 5), "q2": date(2026, 7, 30)}
    # the same filing can never satisfy two events, and a verified date uses a tight window
    far = ev("far", "KKR", date(2026, 7, 10), basis="official")
    assert edgar.match([far], fs, date(2026, 10, 12)) == []
    assert edgar.match([ev("fut", "KKR", date(2026, 11, 9))], fs, date(2026, 10, 12)) == []   # future: nothing to match


def test_6k_matched_by_filing_date_and_document_name():
    s = sub([("6-K", "2026-07-29", "2026-06-30", "", "edgar2q26ubsgroupag.htm", "", "0001610520-26-1"),
             ("6-K", "2026-07-01", "2026-06-30", "", "ubs-rep.htm", "DIRECTOR SHAREHOLDING", "0001610520-26-0")])
    fs = {"UBS": edgar.parse_submissions(1610520, s)}
    (e, f), = edgar.match([ev("q2", "UBS", date(2026, 7, 28))], fs, date(2026, 10, 12))
    assert f.event_date == date(2026, 7, 29)        # filing date, not the period-end reportDate


def test_headline_cleaning():
    t = "1 2 a1q26gsearningsresults Exhibit 99.1 Blackstone Reports First Quarter 2026 Results New York, April 23, 2026: Blackstone today"
    h, s = edgar.headline_and_summary(t, None, "fallback")
    assert h.startswith("Blackstone Reports First Quarter 2026 Results") and "today" in s
    h, s = edgar.headline_and_summary("nav nav menu 02 Results of Operations", None, "KKR Q1 released")
    assert h == "KKR Q1 released" and "SEC" in s and "nav" not in s     # junk is never shown as the summary


def test_detect_end_to_end_with_mock_sec():
    def handler(req: httpx.Request):
        u = str(req.url)
        if u.endswith("CIK0001404912.json"):
            return httpx.Response(200, json=KKR)
        if u.endswith("/index.json"):
            return httpx.Response(200, json={"directory": {"item": [{"name": "kkr-20260730.htm"}, {"name": "q226earningsrelease_vf.htm"}]}})
        if u.endswith("q226earningsrelease_vf.htm"):
            return httpx.Response(200, headers={"content-type": "text/html"},
                                  text="<html><body><p>KKR Reports Second Quarter 2026 Results. AUM $796 billion.</p></body></html>")
        return httpx.Response(404)
    e = ev("q2", "KKR", date(2026, 8, 4))
    hits = asyncio.run(edgar.detect([e], date(2026, 10, 12), httpx.AsyncClient(transport=httpx.MockTransport(handler))))
    (ev_, f, url, text), = hits
    assert url.endswith("q226earningsrelease_vf.htm") and "AUM $796 billion" in text
    edgar.apply(ev_, f, url, text, "now")
    assert (e.status, e.basis, e.date) == ("reported", "official", date(2026, 7, 30))
    assert e.result.headline.startswith("KKR Reports Second Quarter 2026 Results") and "sec.gov" not in "x"


def _hit(e: Event, filed="2026-07-30"):
    f = edgar.Filing(1404912, "8-K", date.fromisoformat(filed), date.fromisoformat(filed), "2.02", "kkr.htm", "8-K", "0001404912-26-000022")
    return [(e, f, "https://www.sec.gov/Archives/edgar/data/1404912/000140491226000022/ex.htm", "KKR Reports Second Quarter 2026 Results. AUM $796 billion.")]


def test_run_applies_edgar_silently_for_old_releases_and_works_without_llm(tmp_path: Path, monkeypatch):
    data = tmp_path / "events.json"
    write_data(data, build_events())
    ref = next(e for e in build_events() if e.id == "kkr-q2-2026")

    async def fake(events, today, client=None):
        e = next(x for x in events if x.id == "kkr-q2-2026")
        return _hit(e)
    monkeypatch.setattr("agent.run.edgar_detect", fake)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    sent = []
    with patch.object(run, "send_email", lambda u: sent.extend(u)):
        rc = run.main(["--data", str(data), "--today", "2026-10-12"])          # no model, no key
    assert rc == 0 and sent == []                                                # >14 days old: recorded, not emailed
    saved = json.loads(data.read_text())
    k = next(e for e in saved["events"] if e["id"] == "kkr-q2-2026")
    assert (k["status"], k["date"]) == ("reported", "2026-07-30") and ref.date.isoformat() == "2026-08-04"
    assert saved["state"]["llm"] is False and saved["state"]["last_stats"]["edgar"] == 1
    assert saved["updates"][0]["notified"] is True


def test_recent_release_is_emailed_and_enriched_by_llm(tmp_path: Path, monkeypatch):
    data = tmp_path / "events.json"
    write_data(data, build_events())

    async def fake(events, today, client=None):
        return _hit(next(x for x in events if x.id == "kkr-q2-2026"), filed="2026-10-10")
    monkeypatch.setattr("agent.run.edgar_detect", fake)

    def fn(messages, info):
        tool = info.output_tools[0]
        props = tool.parameters_json_schema["properties"]
        if "metrics" in props and "released" not in props and "reports" not in props:       # the enrichment agent
            args = {"headline": "KKR Q2 2026", "summary": "AUM grew.", "metrics": ["AUM $796bn"]}
        elif "reports" in props:
            args = {"reports": []}
        else:
            args = {"released": False}
        return ModelResponse(parts=[ToolCallPart(tool.name, args)])
    sent = []
    with patch.object(run, "send_email", lambda u: sent.extend(u)):
        run.main(["--data", str(data), "--today", "2026-10-12", "--no-discover"], model=FunctionModel(fn))
    k = next(e for e in json.loads(data.read_text())["events"] if e["id"] == "kkr-q2-2026")
    assert k["result"]["metrics"] == ["AUM $796bn"] and any(u["event_id"] == "kkr-q2-2026" for u in sent)
