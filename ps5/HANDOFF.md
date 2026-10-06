# Handoff: MGT-403 Problem Set 5 (Cost Drivers in Childcare)

You are picking up a task from a claude.ai chat session. This file is the full context.
Goal: build the PS5 dataset and produce answers to questions 1-7 below, with real numbers.

**Status:** nothing has been run yet. The chat sandbox could not reach the Census or BLS servers
(`403 host_not_allowed`), so no data was downloaded and no results exist. Everything below is
setup, conventions, and draft code. Claude Code should run on a machine with normal internet access.

## Secrets

- A Census API key was pasted in the chat. It is deliberately NOT in this file.
- Read it from the environment: `export CENSUS_API_KEY=...` (ask the user to set it).
- The user was advised to regenerate the key at census.gov since it appeared in a chat.

## The assignment (verbatim from the user, last item truncated in the paste)

Problem Set 5 - Cost Drivers in Childcare

1. Use the Census API to download ACS 5-year estimates for the explanatory variables listed above
   (the list was NOT included in the paste; see "Predictors" below), at the county level, 2015-2022.
2. Use the BLS OEWS files to download childcare-worker (SOC 39-9011) wage earnings at the area
   level, 2015-2022.
3. Merge OEWS area wages down to counties with the provided `county_oews_crosswalk.csv` (join on
   `[year, oews_area]`: zero-pad the OEWS area field in the BLS data to a seven-character variable
   first so it matches the crosswalk format), attach ACS county data, and label metros with the
   `area_title` field from the same crosswalk. The result is identified by year x county. Keep only
   counties in an OEWS metropolitan area (`oews_area` begins `00`). Sanity-check that nearly all
   counties have non-missing wages (BLS suppresses a small number of area-year cells, expect roughly
   1% missing); if many are missing, verify the merge used the crosswalk correctly.
4. Build a descriptive table (mean / SD / number of observations) of each predictor in 2022.
5. Convert dollar values to 2022 dollars (CPI-U) and plot trends in childcare-worker wages and
   rents over time.
6. Owners of childcare firms claim rising childcare-worker wages were an important driver of
   increased costs after Covid-19. Test the null that average inflation-adjusted wage earnings for
   childcare workers were the same in 2022 as in 2019. Formulate H0 and HA; run the appropriate
   test; report the test statistic and p-value; interpret (reject? what does it say about the
   providers' claim?).
7. Bivariate regression, 2022 data: regress childcare-worker wages on the share of women 25+ with a
   bachelor's degree or higher (female college share). Report the coefficient. Can you reject that
   it equals zero? Interpret the coefficient in words. (Text cut off after "Interpret the
   coefficient in word"; assume "words".)

## Files available

In the chat uploads (user should place these in the working directory):

- `county_oews_crosswalk.csv` - county x year -> OEWS area. 25,859 rows, 3,233 counties, years
  2015-2022. Columns: `county_fips` (5-char, text), `state_abbr`, `year`, `oews_area` (already a
  7-char text code with leading zeros, e.g. `0033860`), `area_title` (e.g. "Montgomery, AL").
  Read everything as text (`dtype=str`) so leading zeros survive, then cast `year` to int.
- `hw-4-project-files.zip` - the instructor's answer-key package for **Problem Set 4** (not PS5):
  `code/answers_common.py`, `code/ps4_answers.py`, `data/ps4_*.csv`, `data/ps4_results.json`,
  `figures/`, and a README. It has NO wage or ACS data and no PS5 script. Its value is the course
  conventions and helper functions (below). `answers_common.py` also contains `build_ps5_file()`
  and `PS5_PREDICTORS`, which show how the PS5 file is structured, but it depends on pipeline
  intermediates (parquet files, `config.py`) that are not included.
- `README.md` - the student package README (describes `ASSIGNMENT.pdf`, which was not in the upload).
  The full assignment PDF would give the exact ACS variable list and CPI instructions; ask the user
  for it if available.

## Course conventions (taken from the PS4 key; follow these)

- Test statistics are **z-statistics with standard-normal p-values** (large-sample convention).
  The t-based p-value is only a reference. Do not use `ttest_rel` as the headline result.
- 95% CIs use **1.96**.
- Regressions use **conventional (constant-variance) OLS standard errors**, laid out like Excel's
  regression output. Do NOT cluster or use robust SEs in the headline result (clustering by
  `oews_area` can be mentioned as a robustness note, since counties in one metro share a wage).
- Sample = OEWS metro counties (`oews_area` starts with `00`), applied **year by year** (a county
  can be metro in some years and not others). Read `oews_area` as text.
- **Drop Puerto Rico** (state FIPS `72`) everywhere. The crosswalk places 69 municipios in metro
  areas; the course drops them across all problem sets for a consistent county set.
- Dollars: real 2022 dollars = nominal x (CPI-U annual avg 2022 / CPI-U annual avg of that year),
  BLS series `CUUR0000SA0`. The eight annual values are in the instructor's `config.py` (not
  provided); fetch from BLS/FRED or ask the user.
- Wage variable: OEWS **annual mean** (`a_mean`) for SOC 39-9011, then deflated (`a_mean_real`).
  Rent: ACS median gross rent, deflated. Per-capita income: deflated.
- Say which unit of analysis you used; the key accepts defended alternatives. Counties in the same
  metro share one OEWS wage, so area-level versions of tests are a reasonable robustness check.
- The PS4 key's helper functions (in `answers_common.py`) worth reusing or mirroring:
  `one_sample_z`, `welch_z(a, b)`, `paired_z(d)`, `mean_ci`, `ols(df, y, xcols)` (conventional SEs),
  `terms_from_res`, `summary_table` (mean / SD with ddof=1 / N), `is_metro`, `deflator`.

## Predictors (ACS) - partially unknown

The assignment's variable list was not in the chat. From `answers_common.py` the PS5 predictors are:

| column | meaning |
|---|---|
| `a_mean_real` | childcare-worker annual mean earnings (real 2022$) (OEWS) |
| `median_gross_rent_real` | median gross rent, monthly (real 2022$) |
| `per_capita_income_real` | per-capita income (real 2022$) |
| `pop_total` | total population |
| `kids_under6` | own children under 6 |
| `kids_under6_allpar_lf` | under-6 with all resident parents in labor force |
| `under6_share` | kids_under6 / pop_total |
| `under6_careneed_share` | kids_under6_allpar_lf / pop_total |
| `female_college_share` | share of women 25+ with bachelor's or higher |
| `female_ftyr_share` | share of women 16-64 employed full-time year-round |

The exact ACS table/variable codes are NOT confirmed. Unverified suggestions only:
`B25064_001E` (median gross rent), `B19301_001E` (per-capita income), `B01003_001E` (population),
`B15002` female cells (019 = female 25+ total; 032-035 = bachelor's, master's, professional,
doctorate). Verify every code against the Census variable list for each year (2015-2022), and
ask the user for the handout's list. Notes: Census uses large negative sentinel values (e.g.
-666666666) for missing; convert to NaN. ACS 5-year county data exist for all years 2015-2022.
Connecticut's county definitions changed in the 2022 data (the PS4 key mentions "legacy CT
counties retained in 2022"); check the crosswalk/ACS FIPS match for CT.

## Pipeline plan

1. **ACS.** For each year 2015-2022, `https://api.census.gov/data/{year}/acs/acs5` with
   `get=<vars>&for=county:*&key=$CENSUS_API_KEY`. Build `county_fips = state + county` (text).
   Compute derived shares. Drop state `72`.
2. **OEWS.** Download `https://www.bls.gov/oes/special-requests/oesm{yy}all.zip` for each year
   (bls.gov may block scripted downloads; if so, have the user download manually or set a
   browser-like User-Agent). Use the "all data" file; lowercase column names (casing varies by
   year). Filter `occ_code == "39-9011"`. Keep `area`, `area_title`, `a_mean`, `tot_emp`.
   Pad `area` to 7 chars with `str.zfill(7)` -> `oews_area`. Suppressed cells (`*`, `#`) -> NaN
   via `pd.to_numeric(errors="coerce")`.
3. **Merge.** `crosswalk.merge(oews, on=["year","oews_area"], how="left")`, then merge ACS on
   `["year","county_fips"]` with `validate="one_to_one"`. Keep `oews_area.str.startswith("00")`,
   drop FIPS `72`. Assert uniqueness of `year x county_fips`. Expect ~1% missing wages; if far more,
   the padding or text dtype is wrong. Label metros with the crosswalk `area_title`.
4. **Descriptive table (2022):** mean, SD (ddof=1), N for each predictor in the table above.
5. **Real dollars + trends:** deflate wages, rent, per-capita income to 2022$. Plot mean real wage
   and mean real rent by year (separate panels or both indexed to 2015=100). Consider a balanced
   panel version (counties observed in all years) plus an all-counties version, as the PS4 key does,
   and state the choice.
6. **Q6.** H0: mu_2022 = mu_2019 (real childcare-worker wage); HA: mu_2022 != mu_2019 (two-sided;
   a one-sided "increase" version matches the owners' claim, mention it). Primary test: **paired
   z-test** on counties with a wage in both 2019 and 2022 (`d = wage_2022 - wage_2019`,
   `z = mean(d)/(sd(d)/sqrt(n))`, p from the normal). Alternative: Welch two-sample z. Report mean
   change, SE, z, p, N. Interpretation caveat: a significant real rise supports "wages rose" but
   does not by itself show wages were a *major* cost driver.
7. **Q7.** 2022 only: `wage_real ~ female_college_share` with conventional OLS SEs. Report
   coefficient, SE, t, p, 95% CI, N, R^2. Interpret in the share's units (state whether the share
   is 0-1 or 0-100; e.g. "a 10-point higher share is associated with $0.10*beta higher annual real
   wages"). It is an association, not a causal effect (female college share likely proxies for
   local income, cost of living, and labor-market strength).

## Draft code (not yet run)

```python
import os, numpy as np, pandas as pd, requests, statsmodels.api as sm
from scipy import stats

KEY = os.environ["CENSUS_API_KEY"]
YEARS = range(2015, 2023)

# --- ACS (replace/verify variable codes) ---
acs_vars = {"B25064_001E": "median_gross_rent", "B19301_001E": "per_capita_income",
            "B01003_001E": "pop_total"}   # + the rest from the handout
frames = []
for yr in YEARS:
    r = requests.get(f"https://api.census.gov/data/{yr}/acs/acs5",
                     params={"get": ",".join(acs_vars), "for": "county:*", "key": KEY})
    r.raise_for_status(); j = r.json()
    d = pd.DataFrame(j[1:], columns=j[0]); d["year"] = yr
    d["county_fips"] = d["state"] + d["county"]
    frames.append(d)
acs = pd.concat(frames).rename(columns=acs_vars)
for c in acs_vars.values():
    acs[c] = pd.to_numeric(acs[c], errors="coerce")
    acs.loc[acs[c] < 0, c] = np.nan            # Census negative sentinels

# --- OEWS ---
oews = []
for yr in YEARS:
    df = pd.read_excel(f"oesm{str(yr)[2:]}all/all_data_M_{yr}.xlsx", dtype={"AREA": str})
    df.columns = df.columns.str.lower()
    df = df[df["occ_code"] == "39-9011"].copy(); df["year"] = yr
    df["oews_area"] = df["area"].astype(str).str.zfill(7)
    df["a_mean"] = pd.to_numeric(df["a_mean"], errors="coerce")
    oews.append(df[["year", "oews_area", "a_mean"]])
oews = pd.concat(oews)

xw = pd.read_csv("county_oews_crosswalk.csv", dtype=str); xw["year"] = xw["year"].astype(int)
panel = (xw.merge(oews, on=["year", "oews_area"], how="left")
           .merge(acs, on=["year", "county_fips"], how="left", validate="one_to_one"))
panel = panel[panel["oews_area"].str.startswith("00") & ~panel["county_fips"].str.startswith("72")]
assert not panel.duplicated(["year", "county_fips"]).any()
print("missing wage share:", panel["a_mean"].isna().mean())   # expect ~0.01

# --- real dollars (cpi: dict year -> CPI-U annual average, CUUR0000SA0) ---
panel["defl"] = panel["year"].map(lambda y: cpi[2022] / cpi[y])
panel["wage_real"] = panel["a_mean"] * panel["defl"]

# --- Q6: paired z ---
w = (panel[panel.year.isin([2019, 2022])]
     .pivot(index="county_fips", columns="year", values="wage_real").dropna())
d = w[2022] - w[2019]; se = d.std(ddof=1) / np.sqrt(len(d)); z = d.mean() / se
print(len(d), d.mean(), se, z, 2 * stats.norm.sf(abs(z)))

# --- Q7: OLS, conventional SEs ---
d22 = panel[panel.year == 2022].dropna(subset=["wage_real", "female_college_share"])
res = sm.OLS(d22["wage_real"].astype(float),
             sm.add_constant(d22["female_college_share"].astype(float))).fit()
print(res.summary()); print(res.conf_int())
```

## Open questions to resolve with the user

1. The exact ACS variable list from the handout (and whether tables beyond those above are needed).
2. Whether to report Q7's share as a fraction or percentage points.
3. CPI-U annual averages (fetch from BLS/FRED `CUUR0000SA0`, or the instructor's `config.py`).
4. Preferred language/tooling (Python assumed; the course key is Python; user did not request Stata).
5. Whether to also produce figures/tables as files (PNG/CSV) and a short written answer document.

## Deliverables suggested

- `ps5_panel.csv` (year x county), descriptive table CSV, trend figure PNG.
- A short write-up with H0/HA, test statistic and p-value (Q6) and coefficient, test, and
  interpretation (Q7), in the course's z-test / conventional-SE conventions.
- Do not include the Census API key in any output file.
