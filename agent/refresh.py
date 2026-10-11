"""No-LLM refresh of news headlines, 10y yields and ACLED counts -> data/live.json (+ live.js).

  python -m agent.refresh
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from . import acled, fx, news, yields
from .seed import atomic_write

LIVE = Path(__file__).resolve().parent.parent / "data" / "live.json"


def write_live(path: Path, payload: dict) -> None:
    text = json.dumps(payload, indent=1)
    atomic_write(path, text + "\n")
    atomic_write(path.with_suffix(".js"), "window.LIVE_DATA = " + text + ";\n")


async def run(path: Path = LIVE) -> dict:
    prev = json.loads(path.read_text()) if path.exists() else {}
    payload = dict(prev)
    payload["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload["news"] = await news.refresh(prev.get("news"))
    payload["yields"] = await yields.refresh(prev.get("yields"))
    payload["fx"] = await fx.refresh(prev.get("fx"))
    try:
        payload["conflict"] = await acled.refresh()
    except Exception as exc:
        payload["conflict"] = {**prev.get("conflict", {}), "status": "error", "error": f"{type(exc).__name__}: {exc}"}
    write_live(path, payload)
    return payload


def main() -> int:
    p = asyncio.run(run())
    ok = [b for b, y in p["yields"].items() if y.get("value") is not None and not y.get("error")]
    print(f"news: {len(p['news'])} headlines; yields ok: {len(ok)}; fx pairs: {len(p['fx']['pairs'])}; acled: {p['conflict'].get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
