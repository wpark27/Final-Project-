import json

import pytest
from fastapi.testclient import TestClient

from agent import fx
from agent.seed import build_events

ECB_XML = """<?xml version="1.0"?><gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref"><Cube>
 <Cube time='2026-10-09'><Cube currency='USD' rate='1.1206'/><Cube currency='GBP' rate='0.84763'/><Cube currency='JPY' rate='177.34'/></Cube>
 <Cube time='2026-10-08'><Cube currency='USD' rate='1.1186'/><Cube currency='GBP' rate='0.8468'/><Cube currency='JPY' rate='177.5'/></Cube>
 </Cube></gesmes:Envelope>"""


def test_fx_cross_rates_and_change():
    out = fx.build(fx.parse_ecb(ECB_XML))
    p = {x["pair"]: x for x in out["pairs"]}
    assert out["as_of"] == "2026-10-09"
    assert p["EUR/USD"]["rate"] == 1.1206
    assert p["GBP/USD"]["rate"] == pytest.approx(1.1206 / 0.84763, rel=1e-5)   # cross via EUR
    assert p["USD/JPY"]["rate"] == pytest.approx(177.34 / 1.1206, rel=1e-5)
    assert p["EUR/USD"]["change_pct"] == pytest.approx((1.1206 / 1.1186 - 1) * 100, abs=0.01)
    assert "USD/CHF" not in p            # CHF absent from feed -> omitted, never invented


def test_fx_failure_keeps_previous_and_flags(monkeypatch):
    import asyncio, httpx
    prev = {"as_of": "2026-10-08", "pairs": [{"pair": "EUR/USD", "rate": 1.1}], "error": None}

    class Boom:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): raise httpx.ConnectError("down")
        async def __aexit__(self, *a): pass
    monkeypatch.setattr(fx.httpx, "AsyncClient", Boom)
    out = asyncio.run(fx.refresh(prev))
    assert out["pairs"] == prev["pairs"] and "ConnectError" in out["error"]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from agent.seed import write_data
    import app.main as m
    write_data(tmp_path / "events.json", build_events())
    (tmp_path / "live.json").write_text(json.dumps({"updated": "2026-10-11T00:00:00+00:00", "news": [],
                                                    "fx": fx.build(fx.parse_ecb(ECB_XML))}))
    monkeypatch.setattr(m, "events_file", m._Cache(tmp_path / "events.json"))
    monkeypatch.setattr(m, "live_file", m._Cache(tmp_path / "live.json"))
    return TestClient(m.app)


def test_api_endpoints(client):
    assert client.get("/api/health").json()["events"] > 250
    ev = client.get("/api/events", params={"layer": "politics", "q": "sweden"}).json()
    assert len(ev) == 1 and ev[0]["kind"] == "election"
    assert all(e["basis"] == "official" for e in client.get("/api/events", params={"basis": "official"}).json())
    jan = client.get("/api/events", params={"start": "2026-01-01", "end": "2026-01-31"}).json()
    assert jan and all(e["date"].startswith("2026-01") for e in jan)
    assert client.get("/api/events/nope").status_code == 404
    assert client.get("/api/events", params={"layer": "bogus"}).status_code == 422
    assert client.get("/api/fx").json()["as_of"] == "2026-10-09"


def test_refresh_requires_token(client, monkeypatch):
    monkeypatch.delenv("REFRESH_TOKEN", raising=False)
    assert client.post("/api/refresh").status_code == 403           # disabled by default
    monkeypatch.setenv("REFRESH_TOKEN", "s3cret")
    assert client.post("/api/refresh").status_code == 401
    assert client.post("/api/refresh", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_only_data_dir_and_index_are_served(client):
    assert client.get("/").status_code == 200
    assert client.get("/data/events.json").status_code == 200
    for bad in ["/agent/run.py", "/.git/config", "/data/../index.html", "/data/%2e%2e/agent/run.py", "/README.md"]:
        assert client.get(bad).status_code == 404, bad


def test_seed_sanity():
    ev = build_events()
    # central-bank decisions and earnings never fall on a weekend
    for e in ev:
        if e.kind in ("earnings", "rate_decision", "minutes", "summit"):
            assert e.date.weekday() < 5, (e.id, e.date)
    assert len({e.id for e in ev}) == len(ev)
