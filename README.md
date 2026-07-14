# Hospital Readmission & Patient Flow Analytics

**End-to-end hospital operations dashboard built with SQL Server, Python, and Power BI**

## 🔗 Live Dashboard

**[View Interactive Dashboard →](ADD_POWER_BI_SERVICE_LINK_HERE)**

*Published via Power BI Service — no login required, fully interactive*

![Dashboard Preview](Screenshots/Executive%20Overview.png)

---

## Business Problem

Hospitals lose money and quality-of-care ratings when patients are readmitted within 30 days of discharge. Without structured analysis, care teams have no visibility into:

- Which diagnosis categories and patient segments drive readmission risk
- Whether shorter stays (early discharge) or longer stays (sicker patients) predict comebacks
- Whether out-of-pocket cost burden correlates with readmission — a genuine access-to-care question in the Indian context
- Whether a small number of "frequent flyer" patients account for a disproportionate share of hospital cost
- Whether a simple, transparent point-based score can flag high-risk patients at discharge

The result is reactive discharge planning instead of proactive — the same high-risk patients keep bouncing back, and no one has the data to prioritize follow-up care.

---

## Solution

An end-to-end analytics build tracking 9,093 hospital encounters across FY 2024-25 at a fictional Delhi-NCR tertiary care hospital — surfacing which patients, conditions, and care patterns actually drive 30-day readmission, validated identically across SQL, Python, and Power BI.

**Key insights the dashboard surfaces:**
- 30-day readmission rate by diagnosis category, age bracket, and length of stay
- Out-of-pocket cost burden by insurance type, and its relationship to readmission
- A composite, transparent 5-factor risk score that separates low-risk from high-risk patients
- The "frequent flyer" segment — a small share of patients driving an outsized share of cost
- A confirmed confounding relationship between medication complexity and comorbidity burden

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python (Pandas, NumPy, Matplotlib, Seaborn) | Synthetic data generation, data quality checks, EDA, correlation analysis |
| SQL Server | Business-question queries — window functions, self-joins, CTEs |
| Power BI (DAX) | Interactive 2-page dashboard |

---

## Dataset

No public, patient-level, Indian hospital readmission dataset exists at usable scale (checked data.gov.in, PMJAY/Ayushman Bharat records, NFHS, ICMR — see `Data/DATA_DICTIONARY.md` for the full search). This dataset was purpose-built to reflect published Indian epidemiology and cost structure rather than being randomized column-by-column.

**3 tables — 9,093 encounters:**

| Table | Rows | Description |
|-------|------|-------------|
| encounters_features | 9,093 | Core fact table — one row per hospital stay, with engineered features pre-baked |
| patients | 7,500 | Patient demographics, city/state, insurance type |
| doctors | 39 | Doctor details across 6 departments |

**Patterns present in the data, and where they came from:**
- Diagnosis category mix weighted to India's actual inpatient disease-burden ordering (Cardiovascular > Diabetes > Respiratory > Maternal/Neonatal > CKD > Surgical), per ICMR disease-burden data
- Respiratory admissions seasonally weighted — Oct-Feb spike (~1.5-1.9x baseline) reflecting NCR's winter AQI-driven admission pattern
- Cardiovascular self-pay out-of-pocket costs calibrated to a ~₹1.3 lakh median, matching the ₹1.15-1.72 lakh range reported in a published Indian tertiary-hospital OOPE study
- Out-of-pocket cost gradient by insurance type: PMJAY ~2-3% OOP, CGHS ~10%, Private Insurance ~25-30%, Self-pay 100%
- Readmission is not a random flag — each patient's 30-day readmission outcome is the output of a logistic risk model (age, comorbidity, medications, LOS, insurance type, discharge disposition), simulated as a genuine second encounter row 3-30 days later, not a pre-baked label
- A small "frequent flyer" tail (patients with 3 admissions in the year) concentrated in elderly, high-comorbidity chronic patients
- 30-day readmission rate: 17.5% overall, ranging from 25.2% (CKD) down to 5.1% (Maternal/Neonatal)

**Known limitation, stated upfront:** this is a synthetic dataset — no real patient data is used or represented. Calibration anchors come from a small number of published single-hospital Indian studies; they're directional guides, not a validated national benchmark. Full methodology in `Data/DATA_DICTIONARY.md`.

---

## Project Structure

```
Hospital-Readmission-Patient-Flow-Analytics/
│
├── Data/
│   ├── patients.csv
│   ├── doctors.csv
│   ├── encounters.csv
│   ├── encounters_features.csv
│   └── DATA_DICTIONARY.md
│
├── SQL/
│   └── business_questions.sql
│
├── Python/
│   ├── generate_data.py
│   ├── eda.py
│   └── EDA_FINDINGS.md
│
├── PowerBI/
│   └── Hospital_Readmission_Patient_Flow_Analytics.pbix
│
├── Screenshots/
│   ├── Executive Overview.png
│   └── Risk Drivers & High-Risk Segments.png
│
└── README.md
```

---

## SQL Business Questions

`SQL/business_questions.sql` covers 11 questions, structured to progress from headline numbers to a composite risk model:

**Q1-Q6 — Core segmentation:** readmission rate by diagnosis category, age bucket, length-of-stay bucket, insurance type/OOP burden, department & doctor level, discharge disposition impact

**Q7 — Medication complexity vs readmission**, including the confounding check later confirmed numerically in Python (r = 0.73 with comorbidity count)

**Q8-Q9 — Self-joins and window functions:** prior-admission count per patient (self-join with a real bug caught mid-development — filtering to index stays only guaranteed the count was always zero, since a patient's second encounter is by construction always a readmission row), and days-since-last-discharge using `LAG()`

**Q10 — Frequent-flyer cost concentration:** a CTE-based patient-level rollup showing 17.5% of patients account for 37.4% of total inpatient cost

**Q11 — Composite risk-tier score:** a transparent, chained-CTE point-based score (age + comorbidity + prior admissions + insurance type + discharge disposition) validated against real readmission rates per tier

Every query documents the business reasoning, why it's written the way it is, and an honest comparison between the expected and actual result — including two real bugs found and fixed, not glossed over.

---

## Python EDA

`Python/eda.py` does the three things SQL can't do well: full-distribution visuals, a proper correlation matrix, and independently re-deriving two SQL results using a completely different technique, as cross-validation rather than a repeat of the same logic:

- `prior_admissions_365d` rebuilt via a sorted time-window loop (not a self-join) — matched the SQL Q8 result exactly (7,500 / 1,311 / 282 patients with 0/1/2 prior admissions)
- The composite risk-tier score rebuilt independently with `pandas.cut` — matched SQL Q11 exactly (9.94% / 21.21% / 26.59%)
- The Q7 confounding check: `num_medications` and `comorbidity_count` correlate at **r = 0.727** — confirming medication complexity is largely a proxy for comorbidity burden, not an independent readmission driver

Full findings in `Python/EDA_FINDINGS.md`.

---

## Dashboard — 2 Pages

### Page 1 — Executive Overview

The headline numbers for hospital leadership.

![Page 1](Screenshots/Executive%20Overview.png)

**KPI Cards:** Total Discharges · Readmission Rate % · Avg LOS · Total Cost · OOP % of Bill

**Visuals:**
- Readmission Rate by Diagnosis Category — CKD and Cardiovascular highest at ~25%, Maternal/Neonatal lowest at 5.1%
- Monthly Discharge & Readmission Trend — dual-axis chart; the visible March dip is a known data-window artifact (the simulation's fiscal-year cutoff leaves late-March discharges with fewer calendar days to be captured as a 30-day readmission), documented via annotation, not a real clinical trend
- Insurance Type Mix — OOP % vs Readmission — Self-pay bears 100% of its own bill and shows the highest readmission rate
- Readmission Rate & Avg Bill by LOS Bucket — both readmission risk and cost scale together as length of stay increases
- Department Summary Table — department-level rates trace exactly back to diagnosis category (1:1 mapping), confirming the join

---

### Page 2 — Risk Drivers & High-Risk Segments

Where readmission risk concentrates, and whether a simple score can flag it.

![Page 2](Screenshots/Risk%20Drivers%20%26%20High-Risk%20Segments.png)

**KPI Cards:** Total High-Risk Encounters · High-Risk Readmission Rate % · Frequent Flyer Cost Share % · LAMA vs Routine Uplift (pp)

**Visuals:**
- Readmission Rate by Age Bucket — the cleanest single driver in the whole project: a monotonic climb from 4.4% (under 18) to 32.5% (75+)
- Readmission Rate by Medication Complexity — the largest bucket-to-bucket spread (5.9% → 29.1%), but confirmed confounded with comorbidity burden rather than an independent driver
- Readmission Rate by Composite Risk Tier — Low (9.9%) to High (26.6%), with most of the separating power sitting between Low and Medium rather than Medium and High
- Discharge Disposition Impact on Readmission — patients discharged LAMA (Left Against Medical Advice) show a real but modest ~28% relative increase in readmission vs Routine
- Frequent-Flyer Patients: Share of Volume vs Cost — 17.5% of patients (2+ encounters) account for 37.4% of total inpatient cost

---

## Key Findings

| Finding | Value | Business Implication |
|---------|-------|---------------------|
| Overall 30-day readmission rate | 17.5% | Roughly 1 in 6 discharges bounces back within a month |
| Highest-risk category | CKD, 25.2% | Nephrology discharge planning needs the most reinforcement |
| Lowest-risk category | Maternal/Neonatal, 5.1% | Acute, non-chronic care — the least readmission-prone segment |
| Age is the cleanest single driver | 4.4% (under 18) → 32.5% (75+) | Age alone, without any other risk factor, is a strong discharge-planning signal |
| LOS predicts readmission and cost together | 10.2% → 28.7% rate, ~4x cost scaling | Extended stays are both a quality and a cost problem, not just one or the other |
| Self-pay patients | 100% OOP, 19.2% readmission (highest) | Cost-driven early discharge and poor follow-up affordability, not a PMJAY-specific effect |
| Doctor-level variation | Confirmed to be sampling noise, not signal | A modeling limitation stated upfront, not a false finding — doctor_id was never fed into the underlying risk model |
| Medication complexity vs comorbidity | r = 0.73 | The strongest single-bucket spread in the project is a confound, not an independent driver — flagged in SQL, confirmed numerically in Python |
| Frequent-flyer cost concentration | 17.5% of patients → 37.4% of cost | A small, identifiable segment is worth disproportionate discharge-planning attention |
| Composite risk score | Low 9.9% → High 26.6% | A transparent, hand-scorable 5-factor system meaningfully separates risk — cleanly between Low/Medium, less so Medium/High |

---

## DAX Measures

Key measures built in Power BI (stored in a dedicated `_Measures` table):

```dax
-- Readmission Rate % (the is_readmission=0 filter is baked into the
-- underlying Total Discharges / Readmitted Count measures, not a page filter,
-- so a slicer can never accidentally silence it)
Readmission Rate % =
DIVIDE([Readmitted Count], [Total Discharges]) * 100

-- Total Discharges (index stays only)
Total Discharges =
CALCULATE(COUNTROWS(encounters_features), encounters_features[is_readmission] = 0)

-- Frequent Flyer Cost Share % -- built on the row-level is_frequent_flyer
-- flag already precomputed in Python, not a re-derived virtual patient table
Frequent Flyer Cost Share % =
DIVIDE(
    CALCULATE([Total Cost], encounters_features[is_frequent_flyer] = TRUE),
    [Total Cost]
) * 100

-- Composite risk-tier score, re-deriving SQL Q11 inside the model
RiskPoints =
VAR a = RELATED(patients[age])
VAR c = encounters_features[comorbidity_count]
VAR p = encounters_features[prior_admissions_365d]
VAR ins = RELATED(patients[insurance_type])
VAR disp = encounters_features[discharge_disposition]
RETURN
    (IF(a >= 75, 2, IF(a >= 61, 1, 0)))
    + (IF(c >= 3, 2, IF(c = 2, 1, 0)))
    + (IF(p >= 1, 2, 0))
    + (IF(ins = "Self-pay", 1, 0))
    + (IF(disp = "LAMA", 1, 0))
```

---

## How to Run

**Data generation (optional — pre-generated CSVs are already in `Data/`):**
1. `pip install pandas numpy` (or `pip install pandas numpy --break-system-packages` on managed environments)
2. Run `python Python/generate_data.py` to regenerate `patients.csv`, `doctors.csv`, `encounters.csv` from scratch
3. Run `python Python/eda.py` to regenerate `encounters_features.csv` and the EDA charts

**SQL setup:**
1. Open SQL Server Management Studio
2. Import CSVs from `Data/` using SSMS Import Flat File wizard (Tasks → Import Flat File)
3. Import in order: doctors → patients → encounters_features
4. Run `SQL/business_questions.sql` query by query — not all at once

**Power BI:**
1. Open `PowerBI/Hospital_Readmission_Patient_Flow_Analytics.pbix`
2. Home → Transform data → Data source settings → point to your local `Data/encounters_features.csv`, `patients.csv`, `doctors.csv`
3. Refresh data

**Or view instantly without any setup:**
[Live Dashboard on Power BI Service](ADD_POWER_BI_SERVICE_LINK_HERE)

---

## Why This Project

Most fresher analytics portfolios use the same generic Kaggle US diabetes readmission dataset. This project was deliberately built around Indian healthcare context instead — real ICMR disease-burden weighting, real PMJAY-era out-of-pocket cost benchmarks, and Indian city/insurance/hospital storytelling — after confirming no usable real Indian patient-level dataset exists publicly.

The project is also built to show genuine cross-tool rigor rather than a single pass through one tool: the same two results (prior-admission count, composite risk score) are independently derived in both SQL (self-join, chained CTEs) and Python (time-window loop, `pandas.cut`) and land on identical numbers — real proof the underlying labels mean what they claim, not a repeated calculation dressed up twice. Bugs found along the way (a self-join filter that silently zeroed out every result, a DAX measure that quietly showed the wrong tier's number) are documented rather than hidden, because catching and explaining them is a stronger interview story than pretending the first version was always right.

---

## About

Built as part of an independent data analytics portfolio to demonstrate end-to-end DA skills — synthetic data design grounded in real epidemiology, SQL engineering, Python EDA, and Power BI dashboard development with genuine cross-tool validation.

**Tools:** SQL Server · Power BI · DAX · Python · Pandas · NumPy · Matplotlib · Seaborn

**Domain:** Healthcare Analytics · Hospital Operations · Readmission Risk

**Connect:** [LinkedIn](https://www.linkedin.com/in/pratikshadandriyal) · [GitHub](https://github.com/pratikshadandriyal)

---

## Other Projects

- [Helpdesk Performance & SLA Analytics](https://github.com/pratikshadandriyal/Helpdesk-Performance-SLA-Analytics) — SQL Server + Power BI + Python, 8,000+ tickets, SLA breach and agent workload analysis
- [SaaS Product Analytics Dashboard](https://github.com/pratikshadandriyal/SaaS-Product-Analytics-Dashboard) — SQL Server + Power BI + Python, 45,000+ records, churn and feature adoption analysis
- [AI Job Displacement Dashboard](https://github.com/pratikshadandriyal/AI-Job-Displacement-Reskilling-Dashboard) — Power BI, 13,700+ job records across 9 countries
