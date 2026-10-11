"""No-LLM refresh of news headlines, 10y yields and ACLED counts -> data/live.json (+ live.js).

  python -m agent.refresh
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from . import acled, news, yields

LIVE = Path(__file__).resolve().parent.parent / "data" / "live.json"


def write_live(path: Path, payload: dict) -> None:
    text = json.dumps(payload, indent=1)
    path.write_text(text + "\n")
    path.with_suffix(".js").write_text("window.LIVE_DATA = " + text + ";\n")


async def run(path: Path = LIVE) -> dict:
    prev = json.loads(path.read_text()) if path.exists() else {}
    payload = dict(prev)
    payload["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload["news"] = await news.refresh(prev.get("news"))
    payload["yields"] = await yields.refresh(prev.get("yields"))
    try:
        payload["conflict"] = await acled.refresh()
    except Exception as exc:
        payload["conflict"] = {**prev.get("conflict", {}), "status": "error", "error": f"{type(exc).__name__}: {exc}"}
    write_live(path, payload)
    return payload


def main() -> int:
    p = asyncio.run(run())
    ok = [b for b, y in p["yields"].items() if y.get("value") is not None and not y.get("error")]
    print(f"news: {len(p['news'])} headlines; yields ok: {len(ok)}; acled: {p['conflict'].get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
