# Sponsor & Private Capital Calendar 2026

Static page (`index.html`) served by a **FastAPI** app (`app/`), a pydantic-ai crawler agent (`agent/`), and an hourly no-LLM data refresh. The page also works as plain static files (GitHub Pages / `file://`) using the embedded snapshot in `data/*.js`.

## What's on the page
- **Running news tab** (top): headlines from Bloomberg, Financial Times, The Economist public RSS feeds. Headline + link only; articles open on the publisher.
- **FX rotating banner** (under the news tape): 12 major pairs from the ECB euro foreign exchange reference rates (official, one fixing per working day, so not live quotes), with day-over-day change. Rotates every 4.5s, pauses on hover, dots to jump, no auto-rotation under `prefers-reduced-motion`.
- **10-year yield widget** per central bank (Fed/US Treasury, ECB AAA curve, BoE gilt, BoJ/MoF JGB, BoC, RBA) with 1-day change, change since the last rate decision and last minutes, and the next decision date. Official series only. SNB, RBI and PBoC show "n/a": no free official daily feed exists, and nothing is made up.
- **Calendar layers**: Markets (earnings, rate decisions, minutes, CB leadership, market reports), Politics (US primaries and Nov 3 midterms, UK, EU summits, European national elections, appointments, announcements), Conflict (Ukraine / Middle East updates + ACLED counts).

## Data integrity: every date says how it was established
`basis` = `official` (issuer / central bank / government notice), `reference` (NCSL / Vote411 / Wikipedia citing official sources), `estimate` (third-party aggregator), `unverified` (this project's cadence guess). The page labels these; guesses are dashed and marked "?". The crawler replaces estimated/unverified dates with announced ones and, after an event, attaches the official release (headline, summary, figures, link). Off-domain "releases" are rejected in code, and a hit needs a URL on the issuer's own site.

Verified at build time (2026-10-11): Fed, BoE, BoJ, BoC, RBA, SNB, RBI decision calendars, ECB Sep/Oct/Dec, Fed/BoJ/SNB minutes dates, European Council H2 dates, Q3 earnings notices for ~17 issuers, EU/UK/US election dates. Everything else starts `unverified`/`estimate` until the crawler confirms it. Not every ECB 2026 date could be verified offline (Feb–Jul), nor PBoC LPR (rule-based, 20th).

## FastAPI
```
uvicorn app.main:app --reload            # page at /, docs at /docs
AUTO_REFRESH=1 uvicorn app.main:app      # also refreshes news/yields/FX hourly in-process (+ LLM crawl every 3h if ANTHROPIC_API_KEY is set)
```
`GET /api/events` (filters: layer, kind, category, region, status, basis, q, start, end), `/api/events/{id}`, `/api/updates`, `/api/live`, `/api/fx`, `/api/health`, and `POST /api/refresh` (disabled unless `REFRESH_TOKEN` is set; then needs `Authorization: Bearer <token>`). Only `/` and `data/` are served, never the repo root.

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

## Review log (five passes, 2026-10-11)
1. **Static/unit**: pyflakes, JS syntax check, 22 tests. Fixed unused imports and a deprecated `utcnow`.
2. **Data audit** (`re-fetches the official pages and diffs the seed`): Fed, BoE, BoC, BoJ decision dates, ECB published dates and Fed minutes dates match their sites exactly. Fixed PBoC LPR estimates that fell on weekends. Added the missing US primaries/runoffs after cross-checking Vote411 against 270toWin.
3. **Front end** (headless Chromium, file:// and http://): no console errors, filters, keyboard, 390/768px no overflow, dark mode, injection test (HTML and `javascript:` URLs in data are neutralised). Fixed the FX banner clipping on phones.
4. **Backend/security**: crawler now follows redirects by hand and refuses any hop off the issuer's domain (and IP literals/localhost); off-site URLs on a "confirmed date" result are dropped; announced dates more than 250 days out are ignored; atomic file writes (the API could previously read a half-written file); email sent in batches of 30 and resumable; yield window spans New Year; ACLED paginated (the API caps a call at 5000 rows).
5. **Facts**: re-read 16 of 17 "official" earnings notices from the pages themselves (Blackstone's site blocks automated reads, so its Oct 22 date rests on search results quoting its notice); US 10y cross-checked to FRED.
