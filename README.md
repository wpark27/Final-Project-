# Sponsor & Private Capital Calendar 2026

Static site (`index.html`) + a pydantic-ai crawler agent (`agent/`).

- **Calendar**: 2026 earnings for listed PE/credit sponsors (Blackstone, KKR, Apollo, Carlyle, Ares, TPG, Blue Owl, Brookfield, EQT, CVC, Partners Group, 3i, ICG, …), bulge-bracket banks, independent advisories (Evercore, Lazard, PJT, Moelis, Houlihan Lokey, PWP, Rothschild), and rate decisions of the Fed, ECB, BoE, BoJ, BoC, RBA, SNB, RBI and PBoC LPR.
- **Dates are projected** (issuer cadence / central-bank published calendars) until the agent confirms them on the official IR site. Verify before relying on them.
- **Agent**: `python -m agent.run` reads only the issuer's own domain, asks the model whether the release has actually happened (structured `ReleaseCheck` output), writes results to `data/events.json`, and emails new updates. Off-domain "releases" are rejected in code. Weekly-style discovery of new market reports/outlooks uses the research pages in `agent/sources.py`.

## Political layer
US primaries + Nov 3 midterms (Senate/House), UK devolved/local elections, European Council summits, and European national elections are seeded (projected). Appointments and leadership changes (US Senate confirmations, UK government, EU Commission/Council/Parliament, FR/DE/IT/ES) are discovered from official pages by the agent.

## Run
```
pip install -r requirements.txt
python -m pytest -q
export ANTHROPIC_API_KEY=...            # model: AGENT_MODEL (default anthropic:claude-sonnet-5-5)
export SMTP_HOST=smtp.gmail.com SMTP_USER=you@gmail.com SMTP_PASSWORD=<app password>
python -m agent.run --dry-run           # try without writing/emailing
python -m agent.run --backfill          # also check past 2026 events
python -m http.server                   # view the site (or just open index.html)
```
Email goes to winstonpark27@gmail.com (override with `NOTIFY_TO`). Unsent emails are retried on the next run.

## Scheduling
`.github/workflows/crawl.yml` runs every 3 hours and commits refreshed data. Add repo secrets `ANTHROPIC_API_KEY`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`. Host the site with GitHub Pages (branch root).
