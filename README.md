# Member Experience Key-Driver Analysis (CMS HCAHPS)

What actually moves the "would you recommend us" number for a high-touch service, and
where should an operations team spend first? This is the patient-experience version of
**NPS root-cause analysis**, built end to end from raw public data.

Self-directed analysis by Sophia Ize-Iyamu. Built from raw data in **DuckDB/SQL** (no BI
tool, no data team), with a standardized **key-driver regression** and an early-warning
segment scan. Prototyped with Claude.

## The data
**CMS HCAHPS** (Hospital Consumer Assessment of Healthcare Providers and Systems), the
standardized US patient-experience survey, from the public CMS Provider Data Catalog. About
**4,800 hospitals and 2.3M completed surveys**. The outcome is the share of patients who
would **definitely recommend** the hospital, the direct analogue of an NPS promoter rate;
the drivers are the experience top-box scores (nurse and doctor communication, medicines,
discharge, cleanliness, quietness). `analysis.py` downloads it on first run.

## What it finds
- **70%** of patients would definitely recommend their hospital nationally.
- A standardized key-driver regression (R-squared 0.58) ranks **nurse communication as the
  strongest driver** of recommendation, ahead of discharge information and doctor
  communication, and well ahead of the physical-environment dimensions.
- **Quietness is the lowest-scoring dimension (56%)** but a weaker lever, so the analysis
  argues against leading with it: prioritize by derived importance, not by the lowest score.
- It flags **early-warning states and a bottom-decile threshold** so a recurring issue is
  caught at the segment level before it spreads.
- Every recommendation is tied to a cited source (CMS/AHRQ methodology; Doyle et al., *BMJ
  Open* 2013; Reichheld, *HBR* 2003).

These results line up with the established HCAHPS literature (communication leads the
drivers; quietness is the perennial low scorer), which is the credibility check.

## Run it
```bash
pip install -r requirements.txt
python analysis.py
```
Outputs land in `./out`: `findings.md` (the full write-up with recommendations and sources)
and the figures.

## Honest limits
Scores are hospital-level, so this is an ecological (facility-level) driver analysis, not an
individual causal estimate. Driver importance uses standardized OLS coefficients (a standard
key-driver method); the dimensions are correlated, so read the coefficients as relative
weights. HCAHPS is CMS risk- and mode-adjusted but still reflects case-mix differences.

## Source
U.S. Centers for Medicare & Medicaid Services (CMS), "Patient survey (HCAHPS) - Hospital,"
from the CMS Provider Data Catalog (Medicare Care Compare). Dataset ID `dgck-syfz`.

- Dataset page: https://data.cms.gov/provider-data/dataset/dgck-syfz
- Direct CSV (fetched by `analysis.py`): https://data.cms.gov/provider-data/api/1/datastore/query/dgck-syfz/0/download?format=csv
- Catalog home (search "HCAHPS" if a link shifts): https://data.cms.gov/provider-data/

HCAHPS is the standardized, publicly reported US patient-experience survey. The figures here
reflect the dataset release downloaded at run time; CMS refreshes it periodically.
