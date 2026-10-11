"""FastAPI server for the calendar: serves the page and a JSON API over the crawler's data files.

  uvicorn app.main:app --reload
  AUTO_REFRESH=1 uvicorn app.main:app      # also refreshes headlines/yields/FX hourly in-process
                                           # (+ the LLM crawl every 3h when ANTHROPIC_API_KEY is set)
Env: REFRESH_TOKEN enables POST /api/refresh (Bearer token); unset = endpoint disabled.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import refresh as live_refresh
from agent.models import Event

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
log = logging.getLogger("calendar")

POLITICS = {"election", "summit", "appointment", "announcement"}


def layer_of(kind: str) -> str:
    return "conflict" if kind == "conflict_update" else "politics" if kind in POLITICS else "markets"


class _Cache:
    """Re-reads a JSON file only when it changes on disk."""

    def __init__(self, path: Path):
        self.path, self._m, self._v = path, None, None

    def get(self) -> dict:
        try:
            m = self.path.stat().st_mtime_ns
        except FileNotFoundError:
            return {}
        if m != self._m:
            try:
                self._v, self._m = json.loads(self.path.read_text()), m
            except json.JSONDecodeError:  # caught mid-write: keep serving the previous snapshot
                return self._v or {}
        return self._v or {}


events_file, live_file = _Cache(DATA / "events.json"), _Cache(DATA / "live.json")


def _events() -> list[Event]:
    return [Event(**e) for e in events_file.get().get("events", [])]


class Health(BaseModel):
    ok: bool
    events: int
    live_updated: str | None
    fx_as_of: str | None


async def _loop(coro_fn, every_s: int, name: str):
    while True:
        try:
            await coro_fn()
        except Exception:  # never let the scheduler die
            log.exception("%s failed", name)
        await asyncio.sleep(every_s)


async def _crawl():
    from agent import run as crawl_run
    await asyncio.to_thread(crawl_run.main, [])


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = []
    if os.environ.get("AUTO_REFRESH") == "1":
        tasks.append(asyncio.create_task(_loop(live_refresh.run, 3600, "refresh")))
        if os.environ.get("ANTHROPIC_API_KEY"):
            tasks.append(asyncio.create_task(_loop(_crawl, 3 * 3600, "crawl")))
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title="Sponsor & Private Capital Calendar", version="2.0", lifespan=lifespan)


@app.get("/api/health", response_model=Health)
def health():
    live = live_file.get()
    return Health(ok=True, events=len(events_file.get().get("events", [])), live_updated=live.get("updated"),
                  fx_as_of=(live.get("fx") or {}).get("as_of"))


@app.get("/api/events", response_model=list[Event])
def list_events(
    layer: Literal["markets", "politics", "conflict"] | None = None,
    kind: str | None = None,
    category: str | None = None,
    region: str | None = None,
    status: Literal["projected", "confirmed", "reported"] | None = None,
    basis: Literal["official", "reference", "estimate", "unverified"] | None = None,
    q: str | None = Query(None, max_length=100),
    start: date | None = None,
    end: date | None = None,
):
    out = []
    for e in _events():
        if layer and layer_of(e.kind) != layer: continue
        if kind and e.kind != kind: continue
        if category and e.category != category: continue
        if region and e.region != region: continue
        if status and e.status != status: continue
        if basis and e.basis != basis: continue
        if start and e.date < start: continue
        if end and e.date > end: continue
        if q and q.lower() not in f"{e.entity} {e.ticker or ''} {e.title} {e.region}".lower(): continue
        out.append(e)
    return out


@app.get("/api/events/{event_id}", response_model=Event)
def get_event(event_id: str):
    for e in _events():
        if e.id == event_id:
            return e
    raise HTTPException(404, "unknown event id")


@app.get("/api/updates")
def updates(limit: int = Query(50, ge=1, le=500)):
    ups = sorted(events_file.get().get("updates", []), key=lambda u: u["detected_at"], reverse=True)
    return ups[:limit]


@app.get("/api/live")
def live():
    """News headlines, 10y yields, FX and conflict counts (as last refreshed)."""
    return live_file.get()


@app.get("/api/fx")
def fx():
    data = live_file.get().get("fx")
    if not data:
        raise HTTPException(503, "FX not loaded yet; run `python -m agent.refresh`")
    return data


def _auth(authorization: str | None = Header(None)):
    token = os.environ.get("REFRESH_TOKEN")
    if not token:
        raise HTTPException(403, "refresh endpoint disabled (REFRESH_TOKEN not set)")
    if not hmac.compare_digest(authorization or "", f"Bearer {token}"):
        raise HTTPException(401, "bad token")


_refresh_lock = asyncio.Lock()


@app.post("/api/refresh", dependencies=[Depends(_auth)])
async def refresh_now():
    if _refresh_lock.locked():
        raise HTTPException(409, "a refresh is already running")
    async with _refresh_lock:
        p = await live_refresh.run()
    return {"updated": p["updated"], "headlines": len(p["news"]), "fx_as_of": p["fx"].get("as_of")}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "index.html")


# Only data/ is exposed (never the repo root: no source, .git or env files).
app.mount("/data", StaticFiles(directory=DATA), name="data")
