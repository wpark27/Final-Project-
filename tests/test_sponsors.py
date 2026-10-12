import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from agent import run
from agent.seed import RESULTS, TRANSACTIONS, VERIFIED_EARNINGS, build_events, write_data, write_sponsors
from agent.sponsors import SPONSORS


def test_every_sponsor_has_a_cited_aum_and_newsroom():
    assert len(SPONSORS) >= 55
    for name, sp in SPONSORS.items():
        assert sp["aum"] and sp["aum_source"].startswith("https://"), name
        assert sp["news_url"].startswith("https://"), name
        assert sp["category"] in ("pe_sponsor", "credit_sponsor", "private_sponsor"), name
    # all previously missed listed sponsors are now covered
    for n in ("Onex", "Antin Infrastructure Partners", "Tikehau Capital", "Eurazeo", "Wendel", "GCM Grosvenor",
              "Patria Investments", "Brookfield Corporation"):
        assert SPONSORS[n]["listed"]


def test_every_listed_sponsor_has_earnings_events():
    ev = build_events()
    have = {e.entity for e in ev if e.kind == "earnings"}
    assert {n for n, s in SPONSORS.items() if s["listed"]} <= have


def test_published_results_only_where_source_given():
    ev = {e.id: e for e in build_events()}
    assert RESULTS and all(r.url.startswith("https://") and r.metrics for r in RESULTS.values())
    for (ent, period) in RESULTS:
        assert (ent, period) in VERIFIED_EARNINGS and VERIFIED_EARNINGS[(ent, period)][1] == "official"
    done = [e for e in ev.values() if e.kind == "earnings" and e.status == "reported"]
    assert {(e.entity) for e in done} >= {"Onex", "Antin Infrastructure Partners", "Tikehau Capital", "Eurazeo",
                                          "Wendel", "GCM Grosvenor", "Patria Investments"}
    assert all(e.result and e.verified_url for e in done)


def test_seeded_transactions_are_sourced_and_flagged():
    tx = [e for e in build_events() if e.kind == "transaction"]
    assert len(tx) == len(TRANSACTIONS) >= 10
    for e in tx:
        assert e.status == "reported" and e.result.url.startswith("https://") and e.verified_url
        assert e.basis in ("official", "reference")
    kkr = next(e for e in tx if "Integer" in e.title)
    assert "Date approximate" in kkr.result.metrics        # date inferred from a URL is disclosed, not hidden


def _discovery_model(calls):
    def fn(messages, info):
        tool = info.output_tools[0]
        if "reports" in tool.parameters_json_schema["properties"]:
            p = str(messages[0])
            calls.append(p)
            args = {"reports": []}
            if "Entity: Bain Capital" in p:
                args = {"reports": [{"type": "transaction", "entity": "Bain Capital", "title": "Bain Capital to acquire Acme",
                                     "url": "https://www.baincapital.com/news/acme", "published": "2026-10-10",
                                     "summary": "Bain Capital agreed to acquire Acme.",
                                     "details": ["Target: Acme", "Value: $1.2bn"]}]}
            return ModelResponse(parts=[ToolCallPart(tool.name, args)])
        return ModelResponse(parts=[ToolCallPart(tool.name, {"released": False})])
    return FunctionModel(fn)


def test_transaction_scan_records_details_and_respects_cadence(tmp_path: Path):
    data = tmp_path / "events.json"
    write_data(data, build_events())
    calls: list[str] = []
    sent = []
    with patch.object(run, "send_email", lambda u: sent.extend(u)):
        run.main(["--data", str(data), "--today", "2026-10-12"], model=_discovery_model(calls))
        saved = json.loads(data.read_text())
        tx = [e for e in saved["events"] if e["kind"] == "transaction" and e["title"] == "Bain Capital to acquire Acme"]
        assert len(tx) == 1 and tx[0]["result"]["metrics"] == ["Target: Acme", "Value: $1.2bn"]
        assert tx[0]["category"] == "private_sponsor" and any(u["type"] == "transaction" for u in sent)
        scanned_first = sum("Entity: Bain Capital" in c for c in calls)
        assert scanned_first == 1 and saved["state"]["last_scan"]["transaction"]
        # a second run straight away must not re-scan 58 newsrooms (cost control)
        calls.clear()
        run.main(["--data", str(data), "--today", "2026-10-12"], model=_discovery_model(calls))
        assert not any("Entity: Bain Capital" in c for c in calls)
    assert saved["state"]["last_stats"]["discovered"] >= 1 and "unreachable" in saved["state"]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import app.main as m
    write_data(tmp_path / "events.json", build_events(), state={"last_run": "2026-10-12T00:00:00+00:00"})
    write_sponsors(tmp_path)
    monkeypatch.setattr(m, "events_file", m._Cache(tmp_path / "events.json"))
    monkeypatch.setattr(m, "sponsors_file", m._Cache(tmp_path / "sponsors.json"))
    monkeypatch.setattr(m, "live_file", m._Cache(tmp_path / "live.json"))
    return TestClient(m.app)


def test_api_deals_layer_sponsors_and_crawler(client):
    deals = client.get("/api/events", params={"layer": "deals"}).json()
    assert deals and all(e["kind"] == "transaction" for e in deals)
    assert client.get("/api/events", params={"layer": "markets", "kind": "transaction"}).json() == []
    priv = client.get("/api/sponsors", params={"listed": False}).json()
    assert len(priv) >= 30 and all(not s["listed"] for s in priv)
    assert client.get("/api/crawler").json()["last_run"].startswith("2026-10-12")
    assert client.get("/api/health").json()["last_crawl"].startswith("2026-10-12")
