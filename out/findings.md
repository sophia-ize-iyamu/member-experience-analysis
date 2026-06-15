# What makes patients recommend a hospital: a key-driver analysis of CMS HCAHPS

**Self-directed analysis · built from raw data in DuckDB/SQL · prototyped with Claude · Sophia Ize-Iyamu**

## Question
For a high-touch healthcare service, what actually moves the "would you recommend us"
number, and where should an operations team spend first? This is the patient-experience
version of NPS root-cause analysis.

## Data
**CMS HCAHPS** (Hospital Consumer Assessment of Healthcare Providers and Systems), the
standardized US patient-experience survey, via the CMS Provider Data Catalog. 4,792
hospitals and roughly 2,302,474 completed surveys in this release. The outcome
is the share of patients who would *definitely recommend* the hospital, the direct analogue
of an NPS promoter rate. Drivers are the experience top-box scores (the share answering at
the top of the scale). All national figures are survey-volume weighted.

## Headline
- **70.3%** of patients would definitely recommend their hospital nationally; **70.0%** give an overall rating of 9-10.
- The weakest experience dimension is **Quietness** at **55.8%** top-box, a well-known soft spot in HCAHPS.

## Key-driver analysis
A standardized regression of recommendation on the six experience dimensions
(R-squared = 0.58) ranks what carries the most weight, controlling for the overlap
between dimensions:

| Driver | Importance (std. beta) | Correlation | Avg top-box |
|---|---|---|---|
| Nurse communication | +0.28 | +0.72 | 77.8% |
| Discharge information | +0.22 | +0.60 | 85.9% |
| Doctor communication | +0.17 | +0.67 | 77.6% |
| Cleanliness | +0.11 | +0.56 | 70.2% |
| Quietness | +0.11 | +0.55 | 55.8% |
| Communication about medicines | +0.02 | +0.62 | 59.3% |

**Read:** the top driver is **Nurse communication** (standardized beta +0.28).
Importance (how much a dimension moves recommendation) is not the same as score (how well
hospitals already do it). The operational priority is the dimension that is both
high-importance and low-scoring.

## Where to act first
The highest-leverage move is the top driver, **Nurse communication** (78%
top-box, with clear headroom toward the roughly 90% the best hospitals reach). Improving the
dimension that carries the most weight on recommendation moves the headline more than an equal
gain elsewhere. The lowest-scoring dimension, **Quietness** (56%), is
tempting to chase, but it is a weaker lever, so it is a secondary priority, not the first.

## Early-warning segments
Recommendation varies widely by geography. The lowest-recommend states (volume above 5,000
surveys) are **MI (65%), NY (66%), DE (66%), AZ (66%), NM (66%)**, all well below the 70% national mark. A
hospital in the bottom decile sits at or below **58%** definitely-recommend, a
practical threshold for flagging a site for review before the number becomes systemic.

## Recommendations
1. **Lead with communication, not amenities.** The driver analysis puts staff-communication
   dimensions above physical-environment ones (cleanliness, quietness) in their pull on
   recommendation. Invest first in nurse communication and discharge information.
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
   58% definitely-recommend threshold and the low-recommend states for review, so a
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
