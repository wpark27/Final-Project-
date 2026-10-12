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
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .agent import (REACHED, UNREACHABLE, build_discovery_agent, build_enrich_agent, build_release_agent, check_event,
                    discover, discover_from_filings, enrich, build_text_discovery_agent)
from .edgar import CIKS, recent_releases
from .edgar import apply as edgar_apply
from .edgar import detect as edgar_detect
from .models import Event, Result
from .notify import EmailNotConfigured, send_email
from .seed import _slug, write_data
from .sources import APPOINTMENT_PAGES, CONFLICT_PAGES, LEADERSHIP_PAGES, RESEARCH_PAGES
from .sponsors import SPONSORS

DATA = Path(__file__).resolve().parent.parent / "data" / "events.json"
LOOKBACK_DAYS = 14      # a verified-date event is checked for its release this long after its date
CONFIRM_WINDOW = 120    # try to confirm unverified/estimated dates this far ahead
EMAIL_BATCH = 30
MAX_AHEAD_DAYS = 250    # ignore announced dates further out than this (likely a mistake or injected text)
RECHECK_DAYS = 3        # don't re-read an event's source more often than this when nothing was found
DISCOVERED = ("market_report", "appointment", "announcement", "leadership", "conflict_update", "transaction")
# how often each discovery topic is re-scanned (hours): keeps LLM cost bounded while the run itself is frequent
SCAN_EVERY_HOURS = {"market_report": 168, "politics": 6, "leadership": 12, "conflict": 6, "transaction": 24}


def load(path: Path) -> tuple[list[Event], list[dict], dict]:
    raw = json.loads(path.read_text())
    return [Event(**e) for e in raw["events"]], raw.get("updates", []), raw.get("state", {})


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


async def crawl(events: list[Event], updates: list[dict], today: date, args, model=None, state: dict | None = None) -> dict:
    state = state if state is not None else {}
    stats = dict(checked=0, released=0, dates_confirmed=0, discovered=0, errors=0, edgar=0)
    llm = model is not None or bool(os.environ.get("ANTHROPIC_API_KEY"))
    state["llm"] = llm
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sem = asyncio.Semaphore(args.concurrency)
    by_id = {e.id: e for e in events}

    seen = {u["id"] for u in updates}

    def note(ev: Event, typ: str, headline: str, summary: str, url: str, metrics=None) -> None:
        uid = f"{ev.id}:{typ}:{ev.date.isoformat()}"
        if uid in seen:
            return
        seen.add(uid)
        # backfilling something that happened weeks ago is recorded on the page but not emailed
        stale = ev.date < today - timedelta(days=LOOKBACK_DAYS)
        updates.append(dict(id=uid, event_id=ev.id, type=typ, entity=ev.entity,
                            headline=headline, summary=summary, metrics=metrics or [], url=url,
                            detected_at=now, notified=stale))

    async def one(ev: Event) -> None:
        async with sem:
            try:
                out = await check_event(release_agent, ev, today)
            except Exception as exc:  # one bad site must not stop the run
                print(f"  ! {ev.id}: {type(exc).__name__}: {exc}")
                stats["errors"] += 1
                return
        stats["checked"] += 1
        ev.last_checked = now
        if out.released and out.url:
            if out.published and out.published != ev.date and abs((out.published - ev.date).days) <= 60:
                ev.date = out.published          # replace a guessed/estimated date with the real one
            ev.status, ev.basis, ev.verified_url = "reported", "official", out.url
            ev.result = Result(headline=out.headline or ev.title, summary=out.summary or "", metrics=out.metrics,
                               url=out.url, published=out.published, detected_at=now)
            stats["released"] += 1
            note(ev, "released", ev.result.headline, ev.result.summary, out.url, out.metrics)
            print(f"  + released: {ev.title}")
        elif out.confirmed_date and today <= out.confirmed_date <= today + timedelta(days=MAX_AHEAD_DAYS) and (
                ev.basis in ("unverified", "estimate") or out.confirmed_date != ev.date):
            changed = out.confirmed_date != ev.date
            ev.date, ev.status, ev.basis = out.confirmed_date, "confirmed", "official"
            ev.verified_url = out.url or ev.source_url
            stats["dates_confirmed"] += 1
            note(ev, "date_confirmed", f"{ev.title}: date announced as {ev.date.isoformat()}"
                 + (" (changed)" if changed else ""),
                 "Date announced on the official source.", ev.verified_url)
            print(f"  ~ confirmed: {ev.title} -> {ev.date}")

    if args.edgar:  # deterministic: SEC filings prove a release happened and give its real date (no LLM needed)
        try:
            hits = await edgar_detect([e for e in events if not args.only or args.only.lower() in e.entity.lower()], today)
        except Exception as exc:
            print(f"  ! edgar pass failed: {type(exc).__name__}: {exc}")
            hits = []
        enrich_agent = build_enrich_agent(model) if llm else None
        for ev, f, url, text in hits:
            r = edgar_apply(ev, f, url, text, now)
            ev.last_checked = now
            stats["edgar"] += 1
            if enrich_agent and text and stats["edgar"] <= args.max_checks:
                try:
                    en = await enrich(enrich_agent, ev, text)
                    r.headline, r.summary, r.metrics = en.headline, en.summary, en.metrics
                except Exception as exc:
                    print(f"  ! enrich {ev.id}: {type(exc).__name__}")
            note(ev, "released", r.headline, r.summary, url, r.metrics)
        print(f"edgar: {len(hits)} release(s) matched to SEC filings")

    if not llm:
        print("no ANTHROPIC_API_KEY: LLM checks and discovery skipped (EDGAR detection only)")
        return stats

    release_agent = build_release_agent(model)  # only built when an LLM is available
    todo = due(events, today, args.only)[: args.max_checks]
    print(f"checking {len(todo)} scheduled events")
    await asyncio.gather(*(one(e) for e in todo))

    if not args.discover:
        return stats
    known = {e.result.url for e in events if e.result}
    # (topic, entity, category, region, default kind, url)
    jobs = [("market_report", ent, "research", "Global", "market_report", url) for ent, url in RESEARCH_PAGES.items()]
    jobs += [("politics", ent, cat, region, "appointment", url) for ent, (cat, region, url) in APPOINTMENT_PAGES.items()]
    jobs += [("leadership", ent, "central_bank", region, "leadership", url) for ent, (region, url) in LEADERSHIP_PAGES.items()]
    jobs += [("conflict", ent, "conflict", "Global", "conflict_update", url) for ent, url in CONFLICT_PAGES.items()]
    jobs += [("transaction", name, sp["category"], sp["region"], "transaction", sp["news_url"]) for name, sp in SPONSORS.items()]
    scans = state.setdefault("last_scan", {})
    nowdt = datetime.now(timezone.utc)
    topics = {t for t in {j[0] for j in jobs}
              if not scans.get(t) or nowdt - datetime.fromisoformat(scans[t]) >= timedelta(hours=SCAN_EVERY_HOURS[t])}
    jobs = [j for j in jobs if j[0] in topics]
    agents = {t: build_discovery_agent(model, t) for t in topics}

    async def scan(topic, entity, cat, region, default_kind, url) -> None:
        async with sem:
            try:
                res = await discover(agents[topic], entity, url, today)
            except Exception as exc:
                print(f"  ! discover {entity}: {type(exc).__name__}: {exc}")
                stats["errors"] += 1
                return
        for r in res.reports:
            if r.url in known or not (today - timedelta(days=30) <= r.published <= today + timedelta(days=1)):
                continue  # already seen, or the date is implausible for "published in the last 14 days"
            known.add(r.url)
            kind = r.type if (topic == "politics" and r.type in ("appointment", "announcement")) else default_kind
            stats["discovered"] += 1
            ev = Event(id=f"{_slug(entity)}-{kind}-{_slug(r.title)[:50]}", kind=kind, entity=entity, category=cat,
                       region=region, date=r.published, title=r.title, status="reported", basis="official",
                       source_url=url, verified_url=r.url,
                       result=Result(headline=r.title, summary=r.summary, metrics=r.details, url=r.url,
                                     published=r.published, detected_at=now))
            if ev.id in by_id:
                continue
            by_id[ev.id] = ev
            events.append(ev)
            typ = {"market_report": "new_report"}.get(kind, kind)
            updates.append(dict(id=f"{ev.id}:new", event_id=ev.id, type=typ, entity=entity, headline=r.title,
                                summary=r.summary, metrics=[], url=r.url, detected_at=now, notified=False))
            print(f"  + {kind}: {entity}: {r.title}")

    async def scan_edgar(entity: str, cat: str, region: str) -> None:
        try:
            filings = await recent_releases(entity, today)
            async with sem:
                res = await discover_from_filings(text_agent, entity, filings, today)
        except Exception as exc:
            print(f"  ! edgar transactions {entity}: {type(exc).__name__}: {exc}")
            stats["errors"] += 1
            return
        for r in res.reports:
            if r.url in known or not (today - timedelta(days=30) <= r.published <= today + timedelta(days=1)):
                continue
            known.add(r.url)
            stats["discovered"] += 1
            ev = Event(id=f"{_slug(entity)}-transaction-{_slug(r.title)[:50]}", kind="transaction", entity=entity,
                       category=cat, region=region, date=r.published, title=r.title, status="reported", basis="official",
                       source_url=r.url, verified_url=r.url,
                       result=Result(headline=r.title, summary=r.summary, metrics=r.details, url=r.url,
                                     published=r.published, detected_at=now))
            if ev.id in by_id:
                continue
            by_id[ev.id] = ev
            events.append(ev)
            updates.append(dict(id=f"{ev.id}:new", event_id=ev.id, type="transaction", entity=entity, headline=r.title,
                                summary=r.summary, metrics=r.details, url=r.url, detected_at=now, notified=False))
            print(f"  + transaction (SEC): {entity}: {r.title}")

    jobs_edgar = []
    if "transaction" in topics:
        text_agent = build_text_discovery_agent(model)
        jobs_edgar = [scan_edgar(n, sp["category"], sp["region"]) for n, sp in SPONSORS.items() if n in CIKS]
    await asyncio.gather(*(scan(*j) for j in jobs), *jobs_edgar)
    for t in topics:
        scans[t] = nowdt.isoformat(timespec="seconds")
    return stats


def main(argv=None, model=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-discover", dest="discover", action="store_false")
    p.add_argument("--no-edgar", dest="edgar", action="store_false")
    p.add_argument("--only")
    p.add_argument("--data", type=Path, default=DATA)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--max-checks", type=int, default=80)
    p.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = p.parse_args(argv)

    events, updates, state = load(args.data)
    stats = asyncio.run(crawl(events, updates, args.today, args, model, state))
    state["last_run"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state["last_stats"] = stats
    state["unreachable"] = sorted(UNREACHABLE - REACHED)  # official pages the crawler could not read this run
    events.sort(key=lambda e: (e.date, e.entity))

    if args.dry_run:
        print("dry run: nothing written, nothing emailed")
        return 0
    write_data(args.data, events, updates, state)  # persist BEFORE emailing so findings are never lost

    pending = [u for u in updates if not u["notified"]]
    for i in range(0, len(pending), EMAIL_BATCH):  # first runs can find many items: several digests, not one huge mail
        batch = pending[i:i + EMAIL_BATCH]
        try:
            send_email(batch)
        except EmailNotConfigured:
            print(f"email not configured (set SMTP_HOST etc.): {len(pending) - i} update(s) stay queued")
            return 0
        except Exception as exc:  # stays notified=False, retried next run
            print(f"email failed ({exc}); will retry next run")
            return 1
        for u in batch:
            u["notified"] = True
        write_data(args.data, events, updates, state)
        print(f"emailed {len(batch)} update(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
