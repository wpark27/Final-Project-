import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import httpx
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from agent import run
from agent.crawler import fetch_text, same_site
from agent.seed import build_events, write_data


def test_same_site_rules():
    base = "https://ir.blackstone.com/news/"
    assert same_site("https://www.blackstone.com/x", base)
    assert not same_site("https://evil.com/blackstone.com", base)
    assert not same_site("https://blackstone.com.evil.com/", base)
    assert not same_site("http://127.0.0.1/", "http://127.0.0.1/")        # raw IPs never count as an issuer
    assert not same_site("http://localhost:8000/", "http://localhost/")
    assert not same_site("javascript:alert(1)", base) and not same_site("file:///etc/passwd", base)


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_redirect_off_site_is_refused_before_any_request():
    hits = []

    def handler(req: httpx.Request):
        hits.append(str(req.url))
        if req.url.host == "ir.example.com":
            return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data"})
        return httpx.Response(200, text="secret", headers={"content-type": "text/html"})

    out = asyncio.run(fetch_text("https://ir.example.com/", "https://ir.example.com/", _client(handler)))
    assert "refused" in out and hits == ["https://ir.example.com/"]   # the second hop was never requested


def test_on_site_redirect_followed_and_text_extracted():
    def handler(req):
        if req.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new"})
        return httpx.Response(200, text="<html><body><nav>x</nav><p>" + "Investor relations news. " * 12 + "Q3 results on <a href='/r'>November 9</a></p></body></html>",
                              headers={"content-type": "text/html"})
    out = asyncio.run(fetch_text("https://ir.example.com/old", None, _client(handler)))
    assert "Q3 results on November 9" in out and "https://ir.example.com/r" in out


def _model(args_for):
    def fn(messages, info):
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args_for(str(messages[0])))])
    return FunctionModel(fn)


def test_offsite_url_on_confirmed_date_is_dropped_and_far_future_date_ignored(tmp_path: Path):
    data = tmp_path / "events.json"
    write_data(data, build_events())
    # prompt-injected page: claims a date years away, pointing at an attacker URL
    m = _model(lambda p: {"released": False, "confirmed_date": "2029-01-01", "url": "javascript:alert(1)"}
               if "Entity: PJT Partners" in p else {"released": False})
    with patch.object(run, "send_email", lambda u: None):
        run.main(["--data", str(data), "--today", "2026-10-11", "--no-discover"], model=m)
    ev = next(e for e in json.loads(data.read_text())["events"] if e["id"] == "pjt-partners-q3-2026")
    assert ev["basis"] == "unverified" and ev["date"] == "2026-10-22"       # untouched

    m = _model(lambda p: {"released": False, "confirmed_date": "2026-11-03", "url": "https://evil.example/x"}
               if "Entity: PJT Partners" in p else {"released": False})
    with patch.object(run, "send_email", lambda u: None):
        run.main(["--data", str(data), "--today", "2026-10-20", "--no-discover"], model=m)
    saved = json.loads(data.read_text())
    ev = next(e for e in saved["events"] if e["id"] == "pjt-partners-q3-2026")
    assert ev["date"] == "2026-11-03"
    assert ev["verified_url"] == ev["source_url"]                           # off-site URL replaced by the official source


def test_emails_are_batched_and_resumable(tmp_path: Path):
    data = tmp_path / "events.json"
    evs = build_events()
    ups = [dict(id=f"u{i}", event_id="x", type="released", entity="E", headline="h", summary="s", metrics=[],
                url="https://a.com", detected_at="2026-10-11T00:00:00+00:00", notified=False) for i in range(65)]
    write_data(data, evs, ups)
    sizes = []

    def flaky(batch):
        sizes.append(len(batch))
        if len(sizes) == 3:
            raise RuntimeError("smtp down")

    with patch.object(run, "send_email", flaky):
        rc = run.main(["--data", str(data), "--today", "2026-10-11", "--no-discover", "--only", "zzz"],
                      model=_model(lambda p: {"released": False}))
    assert rc == 1 and sizes == [30, 30, 5]
    left = [u for u in json.loads(data.read_text())["updates"] if not u["notified"]]
    assert len(left) == 5                                                   # first two batches stay marked sent


def test_atomic_write_leaves_no_tmp(tmp_path: Path):
    write_data(tmp_path / "events.json", build_events())
    assert not list(tmp_path.glob("*.tmp"))


def test_discovery_ignores_implausible_dates_and_offsite_urls(tmp_path: Path):
    data = tmp_path / "events.json"
    write_data(data, build_events())
    def args(p):
        if "Entity: European Commission" in p:
            return {"reports": [
                {"entity": "x", "title": "Old", "url": "https://commission.europa.eu/old", "published": "2020-01-01", "summary": "s"},
                {"entity": "x", "title": "Future", "url": "https://commission.europa.eu/f", "published": "2027-05-05", "summary": "s"},
                {"entity": "x", "title": "Offsite", "url": "https://evil.example/e", "published": "2026-10-09", "summary": "s"},
                {"entity": "x", "title": "Good", "url": "https://commission.europa.eu/g", "published": "2026-10-09", "summary": "s"}]}
        return {"reports": []}
    m = FunctionModel(lambda msgs, info: ModelResponse(parts=[ToolCallPart(
        info.output_tools[0].name, args(str(msgs[0])) if "reports" in info.output_tools[0].parameters_json_schema["properties"] else {"released": False})]))
    with patch.object(run, "send_email", lambda u: None):
        run.main(["--data", str(data), "--today", "2026-10-11"], model=m)
    titles = [e["title"] for e in json.loads(data.read_text())["events"] if e["kind"] in ("appointment", "announcement")]
    assert titles == ["Good"]


def test_javascript_only_page_is_reported_not_shown_to_the_model():
    shell = httpx.Response(200, text="<html><body><div id='root'></div><script>app()</script></body></html>",
                           headers={"content-type": "text/html"})
    out = asyncio.run(fetch_text("https://ir.example.com/", None, _client(lambda r: shell)))
    assert out.startswith("[fetch failed") and "JavaScript" in out
