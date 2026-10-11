"""CLI: crawl official sources, update data/events.json, email new updates.

  python -m agent.run                 # normal scheduled run
  python -m agent.run --dry-run       # no writes, no email
  python -m agent.run --backfill      # also check every past, unverified event this year
  python -m agent.run --only Blackstone
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
from .sources import APPOINTMENT_PAGES, RESEARCH_PAGES

DATA = Path(__file__).resolve().parent.parent / "data" / "events.json"
LOOKBACK_DAYS = 14   # check events this recent for a release
CONFIRM_WINDOW = 45  # try to confirm projected dates this far ahead


def load(path: Path) -> tuple[list[Event], list[dict]]:
    raw = json.loads(path.read_text())
    return [Event(**e) for e in raw["events"]], raw.get("updates", [])


def due(events: list[Event], today: date, backfill: bool, only: str | None) -> list[Event]:
    sel = []
    for e in events:
        if e.status == "reported" or e.kind in ("market_report", "appointment"):
            continue
        if only and only.lower() not in e.entity.lower():
            continue
        d = (e.date - today).days
        if (-LOOKBACK_DAYS <= d <= 0) or (backfill and d < -LOOKBACK_DAYS) or (0 < d <= CONFIRM_WINDOW and e.status == "projected"):
            sel.append(e)
    return sel


async def crawl(events: list[Event], updates: list[dict], today: date, args, model=None) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sem = asyncio.Semaphore(args.concurrency)
    release_agent = build_release_agent(model)
    by_id = {e.id: e for e in events}

    async def one(ev: Event) -> None:
        async with sem:
            try:
                out = await check_event(release_agent, ev, today)
            except Exception as exc:  # one bad site must not stop the run
                print(f"  ! {ev.id}: {type(exc).__name__}: {exc}")
                return
        if out.released and out.url:
            ev.status = "reported"
            ev.result = Result(
                headline=out.headline or ev.title, summary=out.summary or "", metrics=out.metrics,
                url=out.url, published=out.published, detected_at=now,
            )
            updates.append(dict(id=f"{ev.id}:released", event_id=ev.id, type="released", entity=ev.entity,
                                headline=ev.result.headline, summary=ev.result.summary,
                                metrics=out.metrics, url=out.url, detected_at=now, notified=False))
            print(f"  + released: {ev.title}")
        elif out.confirmed_date and ev.status == "projected":
            ev.date, ev.status = out.confirmed_date, "confirmed"
            updates.append(dict(id=f"{ev.id}:date", event_id=ev.id, type="date_confirmed", entity=ev.entity,
                                headline=f"{ev.title} confirmed for {ev.date.isoformat()}",
                                summary="Date announced on the official investor-relations site.",
                                metrics=[], url=ev.source_url, detected_at=now, notified=False))
            print(f"  ~ confirmed: {ev.title} -> {ev.date}")

    todo = due(events, today, args.backfill, args.only)
    print(f"checking {len(todo)} scheduled events")
    await asyncio.gather(*(one(e) for e in todo))

    if args.discover:
        known = {e.result.url for e in events if e.result}
        jobs = [("market_report", ent, "research", "Global", url) for ent, url in RESEARCH_PAGES.items()]
        jobs += [("appointment", ent, cat, region, url) for ent, (cat, region, url) in APPOINTMENT_PAGES.items()]
        agents = {k: build_discovery_agent(model, k) for k in ("market_report", "appointment")}

        async def scan(kind: str, entity: str, cat: str, region: str, url: str) -> None:
            async with sem:
                try:
                    res = await discover(agents[kind], entity, url, today)
                except Exception as exc:
                    print(f"  ! discover {entity}: {type(exc).__name__}: {exc}")
                    return
            for r in res.reports:
                if r.url in known:
                    continue
                known.add(r.url)
                ev = Event(id=f"{_slug(entity)}-{kind}-{_slug(r.title)[:50]}", kind=kind, entity=entity,
                           category=cat, region=region, date=r.published, title=r.title,
                           status="reported", source_url=url,
                           result=Result(headline=r.title, summary=r.summary, url=r.url, published=r.published, detected_at=now))
                if ev.id in by_id:
                    continue
                by_id[ev.id] = ev
                events.append(ev)
                updates.append(dict(id=f"{ev.id}:new", event_id=ev.id, type="new_report" if kind == "market_report" else "appointment",
                                    entity=entity, headline=r.title, summary=r.summary, metrics=[], url=r.url,
                                    detected_at=now, notified=False))
                print(f"  + {kind}: {entity}: {r.title}")

        await asyncio.gather(*(scan(*j) for j in jobs))


def main(argv=None, model=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--backfill", action="store_true")
    p.add_argument("--no-discover", dest="discover", action="store_false")
    p.add_argument("--only")
    p.add_argument("--data", type=Path, default=DATA)
    p.add_argument("--concurrency", type=int, default=4)
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
