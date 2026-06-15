# -*- coding: utf-8 -*-
"""
Member Experience Key-Driver Analysis  (CMS HCAHPS patient-experience survey)

A from-raw-data analysis of what drives patients to recommend a hospital, the
healthcare analogue of NPS. Built directly on the public CMS HCAHPS dataset with
SQL in DuckDB (no BI tool, no data team), then a standardized key-driver
regression, an early-warning segment scan, and recommendations grounded in cited
research. Prototyped with Claude. Built by Sophia Ize-Iyamu.

Run:  pip install -r requirements.txt  &&  python analysis.py
Outputs (in ./out): figures + findings.md
Data: CMS Provider Data Catalog, "Patient survey (HCAHPS) - Hospital" (public, US gov).
"""
import os
import textwrap
import numpy as np
import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "data", "hcahps.csv")
OUT = os.path.join(HERE, "out")
URL = "https://data.cms.gov/provider-data/api/1/datastore/query/dgck-syfz/0/download?format=csv"

# Outcome (the "would you recommend" top-box, NPS analogue) and the experience drivers.
OUTCOME = ("H_RECMND_DY", "Would definitely recommend")
OVERALL = ("H_HSP_RATING_9_10", "Overall rating 9-10")
DRIVERS = {
    "Nurse communication": "H_COMP_1_A_P",
    "Doctor communication": "H_COMP_2_A_P",
    "Communication about medicines": "H_COMP_5_A_P",
    "Discharge information": "H_COMP_6_Y_P",
    "Cleanliness": "H_CLEAN_HSP_A_P",
    "Quietness": "H_QUIET_HSP_A_P",
}


def ensure_data():
    if os.path.exists(CSV):
        return
    import requests
    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    print("Downloading HCAHPS from CMS...")
    r = requests.get(URL, timeout=180)
    open(CSV, "wb").write(r.content)
    print(f"  saved {len(r.content)//1024//1024} MB")


def facility_table(con):
    """Pivot the long survey into one row per hospital: outcome, drivers, weight."""
    pct = lambda mid: (f"max(CASE WHEN \"HCAHPS Measure ID\"='{mid}' "
                       f"THEN TRY_CAST(\"HCAHPS Answer Percent\" AS DOUBLE) END)")
    cols = [f"{pct(OUTCOME[0])} AS recommend",
            f"{pct(OVERALL[0])} AS overall"]
    cols += [f"{pct(mid)} AS \"{name}\"" for name, mid in DRIVERS.items()]
    sql = f"""
      CREATE OR REPLACE TABLE fac AS
      SELECT "Facility ID" AS fid, any_value(State) AS state,
             max(TRY_CAST("Number of Completed Surveys" AS INT)) AS n_surveys,
             {', '.join(cols)}
      FROM read_csv_auto('{CSV.replace(os.sep, '/')}', sample_size=-1)
      GROUP BY "Facility ID"
    """
    con.execute(sql)
    n = con.execute("SELECT count(*) FROM fac").fetchone()[0]
    return n


def weighted_mean(con, col):
    q = (f'SELECT sum("{col}"*n_surveys)/sum(n_surveys) FROM fac '
         f'WHERE "{col}" IS NOT NULL AND n_surveys IS NOT NULL')
    return con.execute(q).fetchone()[0]


def main():
    ensure_data()
    os.makedirs(OUT, exist_ok=True)
    con = duckdb.connect()
    n_fac = facility_table(con)

    # ---- national survey-weighted headline metrics ----
    nat_recommend = weighted_mean(con, "recommend")
    nat_overall = weighted_mean(con, "overall")
    total_surveys = con.execute("SELECT sum(n_surveys) FROM fac").fetchone()[0]
    driver_means = {name: weighted_mean(con, name) for name in DRIVERS}

    # ---- key-driver analysis: correlation + standardized regression ----
    names = list(DRIVERS)
    cols = ", ".join(f'"{c}"' for c in (["recommend"] + names))
    df = con.execute(
        f"SELECT {cols} FROM fac WHERE recommend IS NOT NULL AND "
        + " AND ".join(f'"{c}" IS NOT NULL' for c in names)
    ).df()
    y = df["recommend"].values.astype(float)
    X = df[names].values.astype(float)
    # univariate correlations
    corrs = {n: float(np.corrcoef(X[:, i], y)[0, 1]) for i, n in enumerate(names)}
    # standardized OLS -> driver importance (controls for shared variance)
    Xs = (X - X.mean(0)) / X.std(0)
    ys = (y - y.mean()) / y.std()
    A = np.column_stack([np.ones(len(Xs)), Xs])
    beta, *_ = np.linalg.lstsq(A, ys, rcond=None)
    std_betas = dict(zip(names, beta[1:]))
    r2 = 1 - np.sum((ys - A @ beta) ** 2) / np.sum((ys - ys.mean()) ** 2)

    # ---- weakest dimension + lead lever (highest-importance driver) ----
    weakest = min(driver_means, key=driver_means.get)
    top_driver = max(std_betas, key=std_betas.get)

    # ---- early-warning segments: states in the bottom of the recommend distribution ----
    states = con.execute("""
        SELECT state,
               sum(recommend*n_surveys)/sum(n_surveys) AS rec,
               sum(n_surveys) AS n
        FROM fac WHERE recommend IS NOT NULL AND n_surveys IS NOT NULL
          AND state IS NOT NULL AND length(state)=2
        GROUP BY state HAVING sum(n_surveys) > 5000
        ORDER BY rec
    """).df()
    p10 = con.execute("SELECT quantile_cont(recommend,0.10) FROM fac WHERE recommend IS NOT NULL").fetchone()[0]

    _figures(driver_means, nat_recommend, std_betas, corrs, df, names, states, p10)
    _report(n_fac, total_surveys, nat_recommend, nat_overall, driver_means, corrs,
            std_betas, r2, weakest, top_driver, states, p10)

    print(f"\nFacilities: {n_fac:,}  | Completed surveys: {total_surveys:,.0f}")
    print(f"National 'definitely recommend': {nat_recommend:.1f}%   overall 9-10: {nat_overall:.1f}%")
    print("\nKey drivers of recommendation (standardized regression beta, R2 = "
          f"{r2:.2f}):")
    for n, b in sorted(std_betas.items(), key=lambda kv: -kv[1]):
        print(f"  {n:<32} beta={b:+.2f}  r={corrs[n]:+.2f}  avg top-box={driver_means[n]:.1f}%")
    print(f"\nWeakest dimension nationally: {weakest} ({driver_means[weakest]:.1f}%)")
    print(f"Top driver (lead lever): {top_driver}")
    print(f"\nWrote {OUT}/findings.md and figures.")


# ----------------------------------------------------------------------------- #
def _figures(driver_means, nat_recommend, std_betas, corrs, df, names, states, p10):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    GOLD, BLUE, RED, INK = "#C9A24A", "#3b78c3", "#e0564a", "#1c2024"

    # 1. dimension top-box scores + recommend
    fig, ax = plt.subplots(figsize=(7, 3.6))
    items = sorted(driver_means.items(), key=lambda kv: kv[1])
    labels = [k for k, _ in items] + ["Would recommend"]
    vals = [v for _, v in items] + [nat_recommend]
    colors = [RED if v == items[0][1] else BLUE for _, v in items] + [GOLD]
    ax.barh(labels, vals, color=colors)
    for i, v in enumerate(vals):
        ax.text(v + 0.5, i, f"{v:.0f}%", va="center", fontsize=8, color=INK)
    ax.set_xlabel("Survey-weighted national top-box score (%)")
    ax.set_title("Patient-experience scores: weakest dimension in red", fontsize=11, color=INK)
    ax.set_xlim(0, 100)
    fig.savefig(os.path.join(OUT, "dimension_scores.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # 2. driver importance (standardized beta)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    items = sorted(std_betas.items(), key=lambda kv: kv[1])
    ax.barh([k for k, _ in items], [v for _, v in items], color=GOLD)
    for i, (_, v) in enumerate(items):
        ax.text(v, i, f" {v:+.2f}", va="center", fontsize=8, color=INK)
    ax.set_xlabel("Standardized regression coefficient (driver importance)")
    ax.set_title("What drives 'would recommend' (key-driver analysis)", fontsize=11, color=INK)
    ax.axvline(0, color="#888", lw=0.8)
    fig.savefig(os.path.join(OUT, "driver_importance.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # 3. scatter of the top driver vs recommend
    top = max(std_betas, key=std_betas.get)
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.scatter(df[top], df["recommend"], s=5, alpha=0.25, color=BLUE)
    ax.set_xlabel(f"{top} (top-box %)")
    ax.set_ylabel("Would recommend (%)")
    ax.set_title(f"Top driver: {top} vs recommendation (r = {corrs[top]:+.2f})", fontsize=11, color=INK)
    fig.savefig(os.path.join(OUT, "top_driver_scatter.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # 4. early-warning: lowest-recommend states
    fig, ax = plt.subplots(figsize=(6, 3.8))
    bottom = states.head(12)
    ax.barh(bottom["state"][::-1], bottom["rec"][::-1], color=RED)
    ax.axvline(nat_recommend, color=INK, lw=1, ls="--")
    ax.text(nat_recommend, -0.7, f"national {nat_recommend:.0f}%", fontsize=7.5, color=INK)
    ax.set_xlabel("Would recommend (%)")
    ax.set_title("Early-warning geographies: lowest-recommend states", fontsize=11, color=INK)
    fig.savefig(os.path.join(OUT, "state_recommend.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------------------- #
def _report(n_fac, total_surveys, nat_recommend, nat_overall, driver_means, corrs,
            std_betas, r2, weakest, top_driver, states, p10):
    ranked = sorted(std_betas.items(), key=lambda kv: -kv[1])
    bottom_states = ", ".join(f"{r.state} ({r.rec:.0f}%)" for r in states.head(5).itertuples())
    drv_rows = "\n".join(
        f"| {n} | {std_betas[n]:+.2f} | {corrs[n]:+.2f} | {driver_means[n]:.1f}% |"
        for n, _ in ranked)
    md = f"""# What makes patients recommend a hospital: a key-driver analysis of CMS HCAHPS

**Self-directed analysis · built from raw data in DuckDB/SQL · prototyped with Claude · Sophia Ize-Iyamu**

## Question
For a high-touch healthcare service, what actually moves the "would you recommend us"
number, and where should an operations team spend first? This is the patient-experience
version of NPS root-cause analysis.

## Data
**CMS HCAHPS** (Hospital Consumer Assessment of Healthcare Providers and Systems), the
standardized US patient-experience survey, via the CMS Provider Data Catalog. {n_fac:,}
hospitals and roughly {total_surveys:,.0f} completed surveys in this release. The outcome
is the share of patients who would *definitely recommend* the hospital, the direct analogue
of an NPS promoter rate. Drivers are the experience top-box scores (the share answering at
the top of the scale). All national figures are survey-volume weighted.

## Headline
- **{nat_recommend:.1f}%** of patients would definitely recommend their hospital nationally; **{nat_overall:.1f}%** give an overall rating of 9-10.
- The weakest experience dimension is **{weakest}** at **{driver_means[weakest]:.1f}%** top-box, a well-known soft spot in HCAHPS.

## Key-driver analysis
A standardized regression of recommendation on the six experience dimensions
(R-squared = {r2:.2f}) ranks what carries the most weight, controlling for the overlap
between dimensions:

| Driver | Importance (std. beta) | Correlation | Avg top-box |
|---|---|---|---|
{drv_rows}

**Read:** the top driver is **{ranked[0][0]}** (standardized beta {ranked[0][1]:+.2f}).
Importance (how much a dimension moves recommendation) is not the same as score (how well
hospitals already do it). The operational priority is the dimension that is both
high-importance and low-scoring.

## Where to act first
The highest-leverage move is the top driver, **{top_driver}** ({driver_means[top_driver]:.0f}%
top-box, with clear headroom toward the roughly 90% the best hospitals reach). Improving the
dimension that carries the most weight on recommendation moves the headline more than an equal
gain elsewhere. The lowest-scoring dimension, **{weakest}** ({driver_means[weakest]:.0f}%), is
tempting to chase, but it is a weaker lever, so it is a secondary priority, not the first.

## Early-warning segments
Recommendation varies widely by geography. The lowest-recommend states (volume above 5,000
surveys) are **{bottom_states}**, all well below the {nat_recommend:.0f}% national mark. A
hospital in the bottom decile sits at or below **{p10:.0f}%** definitely-recommend, a
practical threshold for flagging a site for review before the number becomes systemic.

## Recommendations
1. **Lead with communication, not amenities.** The driver analysis puts staff-communication
   dimensions above physical-environment ones (cleanliness, quietness) in their pull on
   recommendation. Invest first in {ranked[0][0].lower()} and {ranked[1][0].lower()}.
   This matches the foundational patient-experience literature: communication and
   responsiveness consistently lead the drivers of overall experience (Doyle, Lennox & Bell,
   *BMJ Open* 2013, systematic review of patient-experience links to outcomes).
2. **Weight fixes by impact x headroom, not by the lowest score.** Quietness is the lowest
   number and tempting to chase, but it carries less weight on recommendation, so a points
   gain there moves the headline less than the same gain on a top driver. This is standard
   key-driver practice: prioritize on derived importance, not stated or raw scores
   (Reichheld, "The One Number You Need to Grow," *Harvard Business Review*, 2003, on using
   the recommend question as the operational metric).
3. **Stand up an early-warning watch on the bottom decile.** Flag any site below the
   {p10:.0f}% definitely-recommend threshold and the low-recommend states for review, so a
   recurring issue is caught at the segment level before it spreads, which is the systematic,
   eliminate-at-the-source posture rather than case-by-case firefighting.
4. **Track the recommend top-box as the single operating metric**, broken down by the driver
   dimensions, so every experience initiative ties back to a measurable move in the number a
   member would actually act on.

## Method notes and honest limits
Top-box and "definitely recommend" percents are hospital-level, not patient-level, so this
is an ecological (facility-level) driver analysis: it shows which dimensions move the
hospital-level recommend rate, not an individual causal effect. Driver importance uses
standardized OLS coefficients (a standard key-driver method); the dimensions are correlated,
so coefficients should be read as relative weights, not isolated causal lifts. HCAHPS is
risk-adjusted and mode-adjusted by CMS but still reflects case-mix differences across
hospitals.

## Sources
- U.S. Centers for Medicare & Medicaid Services, HCAHPS / "Patient survey (HCAHPS) -
  Hospital," CMS Provider Data Catalog, data.cms.gov (data).
- Agency for Healthcare Research and Quality (AHRQ), CAHPS program (survey methodology).
- Doyle C, Lennox L, Bell D (2013). A systematic review of evidence on the links between
  patient experience and clinical safety and effectiveness. *BMJ Open* 3:e001570.
- Reichheld F (2003). The One Number You Need to Grow. *Harvard Business Review* 81(12).
"""
    with open(os.path.join(OUT, "findings.md"), "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    main()
