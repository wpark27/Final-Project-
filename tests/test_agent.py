import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from agent import run
from agent.seed import build_events, write_data


def fake_model(released_for: str):
    """Stands in for the LLM: 'releases' only the event whose title contains `released_for`."""

    def fn(messages, info):
        prompt = str(messages[0])
        ok = released_for in prompt
        args = (
            {"released": True, "headline": "Q3 results", "summary": "Strong quarter.",
             "metrics": ["FRE $1.00/share"], "url": "https://ir.blackstone.com/news/q3", "published": "2026-10-22"}
            if ok else {"released": False}
        )
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

    return FunctionModel(fn)


def test_detect_release_and_email(tmp_path: Path):
    data = tmp_path / "events.json"
    write_data(data, build_events())
    sent = []
    with patch.object(run, "send_email", lambda u: sent.extend(u)):
        rc = run.main(["--data", str(data), "--today", "2026-10-23", "--no-discover"],
                      model=fake_model("Blackstone Q3 2026"))
    assert rc == 0
    saved = json.loads(data.read_text())
    bx = next(e for e in saved["events"] if e["id"] == "blackstone-q3-2026")
    assert bx["status"] == "reported" and bx["result"]["url"].startswith("https://ir.blackstone.com")
    assert [u["event_id"] for u in sent] == ["blackstone-q3-2026"]
    assert all(u["notified"] for u in saved["updates"])
    assert "window.CALENDAR_DATA" in data.with_suffix(".js").read_text()


def test_offsite_url_rejected(tmp_path: Path):
    """A model 'release' pointing off the issuer's domain must be ignored."""
    data = tmp_path / "events.json"
    write_data(data, build_events())
    bad = fake_model("Blackstone Q3 2026")
    with patch.object(run, "send_email", lambda u: None):
        with patch("agent.agent.same_site", lambda a, b: False):
            run.main(["--data", str(data), "--today", "2026-10-23", "--no-discover", "--only", "Blackstone"], model=bad)
    saved = json.loads(data.read_text())
    assert not saved["updates"]


def test_email_failure_keeps_update_pending(tmp_path: Path):
    data = tmp_path / "events.json"
    write_data(data, build_events())
    def boom(u): raise RuntimeError("smtp down")
    with patch.object(run, "send_email", boom):
        rc = run.main(["--data", str(data), "--today", "2026-10-23", "--no-discover"],
                      model=fake_model("Blackstone Q3 2026"))
    assert rc == 1
    saved = json.loads(data.read_text())
    assert saved["updates"] and not saved["updates"][0]["notified"]


def test_due_window():
    evs = build_events()
    today = date(2026, 10, 11)
    ids = {e.id for e in run.due(evs, today, False, None)}
    assert "blackstone-q3-2026" in ids        # 11 days ahead -> confirm date
    assert "blackstone-q1-2026" not in ids     # long past, no backfill


def test_discover_appointment_and_election_result(tmp_path: Path):
    data = tmp_path / "events.json"
    write_data(data, build_events())

    def fn(messages, info):
        tool = info.output_tools[0]
        prompt = str(messages[0])
        if "reports" in tool.parameters_json_schema.get("properties", {}):
            if "Entity: European Commission" in prompt:
                args = {"reports": [{"entity": "European Commission", "title": "New Commissioner appointed",
                                     "url": "https://commission.europa.eu/news/x", "published": "2026-10-09", "summary": "Appointed."}]}
            else:
                args = {"reports": []}
        else:
            args = {"released": False}
        return ModelResponse(parts=[ToolCallPart(tool.name, args)])

    sent = []
    with patch.object(run, "send_email", lambda u: sent.extend(u)):
        run.main(["--data", str(data), "--today", "2026-10-11"], model=FunctionModel(fn))
    saved = json.loads(data.read_text())
    appts = [e for e in saved["events"] if e["kind"] == "appointment"]
    assert len(appts) == 1 and appts[0]["category"] == "eu_politics"
    assert sent and sent[0]["type"] == "appointment"
