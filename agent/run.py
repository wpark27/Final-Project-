"""CLI: crawl official sources, update data/events.json, email new updates.

  python -m agent.run                 # normal scheduled run
  python -m agent.run --dry-run       # no writes, no email
  python -m agent.run --only Blackstone
  python -m agent.run --max-checks 80 # cap on scheduled-event checks per run (cost control)

What it does each run
  1. Scheduled events: for every event whose date is unverified/estimated (or whose release window has
     arrived) it reads the official page and records either the real announced date (e.g. a company's
     "to announce Q3 results on ..." notice), or the published release itself.
  2. Discovery: scans research, government, central-bank leadership and conflict pages for new items.
  3. Emails one digest of everything new; anything that fails to send is retried next run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .agent import build_discovery_agent, build_release_agent, check_event, discover
from .models import Event, Result
from .notify import send_email
from .seed import _slug, write_data
from .sources import APPOINTMENT_PAGES, CONFLICT_PAGES, LEADERSHIP_PAGES, RESEARCH_PAGES

DATA = Path(__file__).resolve().parent.parent / "data" / "events.json"
LOOKBACK_DAYS = 14      # a verified-date event is checked for its release this long after its date
CONFIRM_WINDOW = 120    # try to confirm unverified/estimated dates this far ahead
RECHECK_DAYS = 3        # don't re-read an event's source more often than this when nothing was found
DISCOVERED = ("market_report", "appointment", "announcement", "leadership", "conflict_update")


def load(path: Path) -> tuple[list[Event], list[dict]]:
    raw = json.loads(path.read_text())
    return [Event(**e) for e in raw["events"]], raw.get("updates", [])


def due(events: list[Event], today: date, only: str | None = None) -> list[Event]:
    """Events worth reading the official source for now, most valuable first."""
    sel = []
    for e in events:
        if e.status == "reported" or e.kind in DISCOVERED:
            continue
        if only and only.lower() not in e.entity.lower():
            continue
        if e.last_checked and (today - date.fromisoformat(e.last_checked[:10])).days < RECHECK_DAYS:
            continue
        d = (e.date - today).days
        unverified = e.basis in ("unverified", "estimate")
        if unverified and d <= CONFIRM_WINDOW:
            sel.append(e)                       # find the real date / the release itself
        elif not unverified and d <= 0:
            sel.append(e)                       # verified date has arrived: has it been published?
    def tier(e: Event) -> tuple[int, int]:
        d = (e.date - today).days
        unverified = e.basis in ("unverified", "estimate")
        if not unverified and d >= -LOOKBACK_DAYS:
            return 0, -d    # verified date just arrived: fetch the release
        if unverified and d >= 0:
            return 1, d     # upcoming: find the issuer's announced date
        if unverified:
            return 2, -d    # past guess: find the real date / release (backfill, most recent first)
        return 3, -d        # old verified event: backfill its result

    return sorted(sel, key=tier)


async def crawl(events: list[Event], updates: list[dict], today: date, args, model=None) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sem = asyncio.Semaphore(args.concurrency)
    release_agent = build_release_agent(model)
    by_id = {e.id: e for e in events}

    def note(ev: Event, typ: str, headline: str, summary: str, url: str, metrics=None) -> None:
        updates.append(dict(id=f"{ev.id}:{typ}:{ev.date.isoformat()}", event_id=ev.id, type=typ, entity=ev.entity,
                            headline=headline, summary=summary, metrics=metrics or [], url=url,
                            detected_at=now, notified=False))

    async def one(ev: Event) -> None:
        async with sem:
            try:
                out = await check_event(release_agent, ev, today)
            except Exception as exc:  # one bad site must not stop the run
                print(f"  ! {ev.id}: {type(exc).__name__}: {exc}")
                return
        ev.last_checked = now
        if out.released and out.url:
            if out.published and out.published != ev.date and abs((out.published - ev.date).days) <= 60:
                ev.date = out.published          # replace a guessed/estimated date with the real one
            ev.status, ev.basis, ev.verified_url = "reported", "official", out.url
            ev.result = Result(headline=out.headline or ev.title, summary=out.summary or "", metrics=out.metrics,
                               url=out.url, published=out.published, detected_at=now)
            note(ev, "released", ev.result.headline, ev.result.summary, out.url, out.metrics)
            print(f"  + released: {ev.title}")
        elif out.confirmed_date and out.confirmed_date >= today and (
                ev.basis in ("unverified", "estimate") or out.confirmed_date != ev.date):
            changed = out.confirmed_date != ev.date
            ev.date, ev.status, ev.basis = out.confirmed_date, "confirmed", "official"
            ev.verified_url = out.url or ev.source_url
            note(ev, "date_confirmed", f"{ev.title}: date announced as {ev.date.isoformat()}"
                 + (" (changed)" if changed else ""),
                 "Date announced on the official source.", ev.verified_url)
            print(f"  ~ confirmed: {ev.title} -> {ev.date}")

    todo = due(events, today, args.only)[: args.max_checks]
    print(f"checking {len(todo)} scheduled events")
    await asyncio.gather(*(one(e) for e in todo))

    if not args.discover:
        return
    known = {e.result.url for e in events if e.result}
    # (topic, entity, category, region, default kind, url)
    jobs = [("market_report", ent, "research", "Global", "market_report", url) for ent, url in RESEARCH_PAGES.items()]
    jobs += [("politics", ent, cat, region, "appointment", url) for ent, (cat, region, url) in APPOINTMENT_PAGES.items()]
    jobs += [("leadership", ent, "central_bank", region, "leadership", url) for ent, (region, url) in LEADERSHIP_PAGES.items()]
    jobs += [("conflict", ent, "conflict", "Global", "conflict_update", url) for ent, url in CONFLICT_PAGES.items()]
    agents = {t: build_discovery_agent(model, t) for t in {j[0] for j in jobs}}

    async def scan(topic, entity, cat, region, default_kind, url) -> None:
        async with sem:
            try:
                res = await discover(agents[topic], entity, url, today)
            except Exception as exc:
                print(f"  ! discover {entity}: {type(exc).__name__}: {exc}")
                return
        for r in res.reports:
            if r.url in known:
                continue
            known.add(r.url)
            kind = r.type if (topic == "politics" and r.type in ("appointment", "announcement")) else default_kind
            ev = Event(id=f"{_slug(entity)}-{kind}-{_slug(r.title)[:50]}", kind=kind, entity=entity, category=cat,
                       region=region, date=r.published, title=r.title, status="reported", basis="official",
                       source_url=url, verified_url=r.url,
                       result=Result(headline=r.title, summary=r.summary, url=r.url, published=r.published, detected_at=now))
            if ev.id in by_id:
                continue
            by_id[ev.id] = ev
            events.append(ev)
            typ = {"market_report": "new_report"}.get(kind, kind)
            updates.append(dict(id=f"{ev.id}:new", event_id=ev.id, type=typ, entity=entity, headline=r.title,
                                summary=r.summary, metrics=[], url=r.url, detected_at=now, notified=False))
            print(f"  + {kind}: {entity}: {r.title}")

    await asyncio.gather(*(scan(*j) for j in jobs))


def main(argv=None, model=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-discover", dest="discover", action="store_false")
    p.add_argument("--only")
    p.add_argument("--data", type=Path, default=DATA)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--max-checks", type=int, default=80)
    p.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = p.parse_args(argv)

    events, updates = load(args.data)
    asyncio.run(crawl(events, updates, args.today, args, model))
    events.sort(key=lambda e: (e.date, e.entity))

    if args.dry_run:
        print("dry run: nothing written, nothing emailed")
        return 0
    write_data(args.data, events, updates)  # persist BEFORE emailing so findings are never lost

    pending = [u for u in updates if not u["notified"]]
    if pending:
        try:
            send_email(pending)
            for u in pending:
                u["notified"] = True
            write_data(args.data, events, updates)
            print(f"emailed {len(pending)} update(s)")
        except Exception as exc:  # stays notified=False, retried next run
            print(f"email failed ({exc}); will retry next run")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
