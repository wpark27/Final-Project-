import json
from pathlib import Path

from agent import run
from agent.notify import EmailNotConfigured
from agent.seed import build_events, write_data


def test_unconfigured_email_keeps_updates_queued_and_does_not_fail(tmp_path: Path, monkeypatch):
    data = tmp_path / "events.json"
    ups = [dict(id="u", event_id="x", type="released", entity="E", headline="h", summary="s", metrics=[],
                url="https://a.com", detected_at="2026-10-11T00:00:00+00:00", notified=False)]
    write_data(data, build_events(), ups)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def unconfigured(batch):
        raise EmailNotConfigured("no smtp")
    monkeypatch.setattr(run, "send_email", unconfigured)
    assert run.main(["--data", str(data), "--today", "2026-10-12", "--no-edgar"]) == 0
    assert json.loads(data.read_text())["updates"][0]["notified"] is False
