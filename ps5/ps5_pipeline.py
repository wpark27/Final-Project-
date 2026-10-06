#!/usr/bin/env python3
"""MGT-403 PS5 pipeline: ACS + OEWS -> county x year panel, Q4-Q7 outputs.

Needs: pandas, numpy, scipy, matplotlib, requests, openpyxl; CENSUS_API_KEY in env.
Run from a machine that can reach api.census.gov and www.bls.gov:
    python ps5/ps5_pipeline.py --xwalk county_oews_crosswalk.csv [--oews-dir DIR]
OEWS zips are downloaded to --oews-dir (default ps5/oews); if bls.gov blocks scripts,
download oesm{yy}all.zip by hand into that directory and re-run.
"""
import argparse, io, os, zipfile, json
import numpy as np, pandas as pd, requests
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

YEARS = range(2015, 2023)
# CPI-U annual average, CUUR0000SA0. Typed from memory: verify against BLS/FRED.
CPI = {2015: 237.017, 2016: 240.007, 2017: 245.120, 2018: 251.107,
       2019: 255.657, 2020: 258.811, 2021: 270.970, 2022: 292.655}
# Unverified codes: the script checks each against the year's variables.json and fails loudly.
RAW = {"B25064_001E": "median_gross_rent", "B19301_001E": "per_capita_income",
       "B01003_001E": "pop_total", "B23008_002E": "kids_under6",
       "B23008_004E": "_lf_both", "B23008_010E": "_lf_father", "B23008_013E": "_lf_mother",
       "B15002_019E": "_f25", "B15002_032E": "_f_ba", "B15002_033E": "_f_ma",
       "B15002_034E": "_f_prof", "B15002_035E": "_f_doc",
       "B23022_025E": "_f1664", "B23022_028E": "_f_ftyr"}
UA = {"User-Agent": "Mozilla/5.0 (course project; contact via student email)"}


def get_acs(key):
    frames = []
    for yr in YEARS:
        base = f"https://api.census.gov/data/{yr}/acs/acs5"
        avail = requests.get(f"{base}/variables.json", timeout=60).json()["variables"]
        bad = [v for v in RAW if v not in avail]
        if bad:
            raise SystemExit(f"{yr}: ACS variables not found: {bad}")
        r = requests.get(base, params={"get": ",".join(RAW), "for": "county:*", "key": key}, timeout=120)
        r.raise_for_status(); j = r.json()
        d = pd.DataFrame(j[1:], columns=j[0]); d["year"] = yr
        d["county_fips"] = d["state"] + d["county"]
        frames.append(d)
    a = pd.concat(frames, ignore_index=True).rename(columns=RAW)
    for c in RAW.values():
        a[c] = pd.to_numeric(a[c], errors="coerce")
        a.loc[a[c] < 0, c] = np.nan  # Census sentinels (-666666666 etc.)
    a["kids_under6_allpar_lf"] = a["_lf_both"] + a["_lf_father"] + a["_lf_mother"]
    a["female_college_share"] = (a["_f_ba"] + a["_f_ma"] + a["_f_prof"] + a["_f_doc"]) / a["_f25"]  # 0-1
    a["female_ftyr_share"] = a["_f_ftyr"] / a["_f1664"]
    a["under6_share"] = a["kids_under6"] / a["pop_total"]
    a["under6_careneed_share"] = a["kids_under6_allpar_lf"] / a["pop_total"]
    a = a[a["state"] != "72"]
    keep = ["year", "county_fips", "median_gross_rent", "per_capita_income", "pop_total", "kids_under6",
            "kids_under6_allpar_lf", "under6_share", "under6_careneed_share",
            "female_college_share", "female_ftyr_share"]
    return a[keep]


def get_oews(dirpath):
    os.makedirs(dirpath, exist_ok=True)
    out = []
    for yr in YEARS:
        z = os.path.join(dirpath, f"oesm{str(yr)[2:]}all.zip")
        if not os.path.exists(z):
            r = requests.get(f"https://www.bls.gov/oes/special-requests/oesm{str(yr)[2:]}all.zip",
                             headers=UA, timeout=300)
            r.raise_for_status(); open(z, "wb").write(r.content)
        with zipfile.ZipFile(z) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith((".xlsx", ".xls"))
                     and "all_data" in n.lower()]
            df = pd.read_excel(io.BytesIO(zf.read(names[0])), dtype={"AREA": str, "area": str})
        df.columns = df.columns.str.lower()
        df = df[df["occ_code"] == "39-9011"].copy()
        df["year"] = yr
        df["oews_area"] = df["area"].astype(str).str.zfill(7)
        df["a_mean"] = pd.to_numeric(df["a_mean"], errors="coerce")  # '*', '#' -> NaN
        out.append(df[["year", "oews_area", "a_mean"]])
    return pd.concat(out, ignore_index=True)


def ols(y, x):
    """Bivariate OLS with conventional SEs; returns dict."""
    X = np.column_stack([np.ones(len(x)), x]); n, k = X.shape
    b = np.linalg.solve(X.T @ X, X.T @ y); e = y - X @ b
    s2 = e @ e / (n - k); se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    t = b / se; p = 2 * stats.t.sf(abs(t), n - k)
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    tc = stats.t.ppf(.975, n - k)
    return dict(n=n, const=b[0], coef=b[1], se=se[1], t=t[1], p=p[1], r2=r2,
                ci95=[b[1] - tc * se[1], b[1] + tc * se[1]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xwalk", default="county_oews_crosswalk.csv")
    ap.add_argument("--oews-dir", default="ps5/oews")
    ap.add_argument("--out", default="ps5/output")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)

    acs, oews = get_acs(os.environ["CENSUS_API_KEY"]), get_oews(a.oews_dir)
    xw = pd.read_csv(a.xwalk, dtype=str); xw["year"] = xw["year"].astype(int)
    p = (xw.merge(oews, on=["year", "oews_area"], how="left")
           .merge(acs, on=["year", "county_fips"], how="left", validate="one_to_one"))
    p = p[p["oews_area"].str.startswith("00") & ~p["county_fips"].str.startswith("72")].copy()
    assert not p.duplicated(["year", "county_fips"]).any()
    print(f"rows {len(p)}; missing wage {p['a_mean'].isna().mean():.3%} (expect ~1%); "
          f"missing ACS {p['median_gross_rent'].isna().mean():.3%}")
    print("missing ACS by year (CT planning regions in 2022?):\n",
          p[p["median_gross_rent"].isna()].groupby("year").size())

    d = p["year"].map(lambda y: CPI[2022] / CPI[y])
    p["a_mean_real"] = p["a_mean"] * d
    p["median_gross_rent_real"] = p["median_gross_rent"] * d
    p["per_capita_income_real"] = p["per_capita_income"] * d
    p.to_csv(f"{a.out}/ps5_panel.csv", index=False)

    # Q4
    cols = ["a_mean_real", "median_gross_rent_real", "per_capita_income_real", "pop_total", "kids_under6",
            "kids_under6_allpar_lf", "under6_share", "under6_careneed_share",
            "female_college_share", "female_ftyr_share"]
    p22 = p[p["year"] == 2022]
    tab = pd.DataFrame({"mean": p22[cols].mean(), "sd": p22[cols].std(ddof=1), "n": p22[cols].count()})
    tab.to_csv(f"{a.out}/q4_descriptives_2022.csv"); print("\nQ4\n", tab)

    # Q5
    g = p.groupby("year")[["a_mean_real", "median_gross_rent_real"]].mean()
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    for axi, c, t in zip(ax, g.columns, ["Childcare-worker annual mean wage", "Median gross rent (monthly)"]):
        axi.plot(g.index, g[c], marker="o"); axi.set_title(t + ", 2022$"); axi.set_xlabel("Year")
    fig.tight_layout(); fig.savefig(f"{a.out}/q5_trends.png", dpi=150)
    g.to_csv(f"{a.out}/q5_trend_means.csv"); print("\nQ5\n", g)

    # Q6: paired z, counties with wage in both years
    w = p[p["year"].isin([2019, 2022])].pivot(index="county_fips", columns="year", values="a_mean_real").dropna()
    dd = w[2022] - w[2019]; se = dd.std(ddof=1) / np.sqrt(len(dd)); z = dd.mean() / se
    q6 = dict(n=len(dd), mean_change=dd.mean(), se=se, z=z, p_two_sided=2 * stats.norm.sf(abs(z)),
              p_one_sided_increase=stats.norm.sf(z))
    print("\nQ6", q6)

    # Q7
    s = p22.dropna(subset=["a_mean_real", "female_college_share"])
    q7 = ols(s["a_mean_real"].to_numpy(float), s["female_college_share"].to_numpy(float))
    print("\nQ7 (share is 0-1)", q7)
    json.dump({"q6": q6, "q7": q7}, open(f"{a.out}/results.json", "w"), indent=2, default=float)


if __name__ == "__main__":
    main()
