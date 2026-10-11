# Sponsor & Private Capital Calendar 2026

Static site (`index.html`) + a pydantic-ai crawler agent (`agent/`) + hourly no-LLM data refresh.

## What's on the page
- **Running news tab** (top): headlines from Bloomberg, Financial Times, The Economist public RSS feeds. Headline + link only; articles open on the publisher.
- **10-year yield widget** per central bank (Fed/US Treasury, ECB AAA curve, BoE gilt, BoJ/MoF JGB, BoC, RBA) with 1-day change, change since the last rate decision and last minutes, and the next decision date. Official series only. SNB, RBI and PBoC show "n/a": no free official daily feed exists, and nothing is made up.
- **Calendar layers**: Markets (earnings, rate decisions, minutes, CB leadership, market reports), Politics (US primaries and Nov 3 midterms, UK, EU summits, European national elections, appointments, announcements), Conflict (Ukraine / Middle East updates + ACLED counts).

## Data integrity: every date says how it was established
`basis` = `official` (issuer / central bank / government notice), `reference` (NCSL / Vote411 / Wikipedia citing official sources), `estimate` (third-party aggregator), `unverified` (this project's cadence guess). The page labels these; guesses are dashed and marked "?". The crawler replaces estimated/unverified dates with announced ones and, after an event, attaches the official release (headline, summary, figures, link). Off-domain "releases" are rejected in code, and a hit needs a URL on the issuer's own site.

Verified at build time (2026-10-11): Fed, BoE, BoJ, BoC, RBA, SNB, RBI decision calendars, ECB Sep/Oct/Dec, Fed/BoJ/SNB minutes dates, European Council H2 dates, Q3 earnings notices for ~17 issuers, EU/UK/US election dates. Everything else starts `unverified`/`estimate` until the crawler confirms it. Not every ECB 2026 date could be verified offline (Feb–Jul), nor PBoC LPR (rule-based, 20th).

## Run
```
pip install -r requirements.txt
python -m pytest -q
python -m agent.refresh                  # headlines + yields (+ACLED if configured), no key needed
export ANTHROPIC_API_KEY=...             # model via AGENT_MODEL (default anthropic:claude-sonnet-5-5)
export SMTP_HOST=smtp.gmail.com SMTP_USER=you@gmail.com SMTP_PASSWORD=<app password>
python -m agent.run --dry-run            # crawl without writing / emailing
python -m agent.run                      # crawl, write data/events.json, email new updates
python -m http.server                    # view the site (or open index.html)
```
Email goes to winstonpark27@gmail.com (override with `NOTIFY_TO`); unsent emails are retried next run.
ACLED: set `ACLED_EMAIL` / `ACLED_PASSWORD` (free account) for 7-day event/fatality counts for Ukraine and Middle East.

## Scheduling (daily updates without prompting)
- `.github/workflows/refresh.yml`: hourly, no secrets required.
- `.github/workflows/crawl.yml`: every 3 hours; needs secrets `ANTHROPIC_API_KEY`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`.
- **GitHub only runs scheduled workflows from the default branch**, so this branch must be merged to `main` for the schedules to fire. Host the site with GitHub Pages (branch root).
