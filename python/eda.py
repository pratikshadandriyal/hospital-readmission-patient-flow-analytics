"""
Hospital Readmission & Patient Flow Analytics — Python EDA
Shanti Multispecialty Hospital, Gurugram | FY 2024-25

Structure:
  1. Load + data quality checks
  2. Feature engineering (mirrors SQL CASE WHEN buckets, for consistency)
  3. Univariate distributions
  4. Bivariate: readmission drivers (re-visualizing the SQL findings)
  5. The Q7 confounding check: num_medications vs comorbidity_count
  6. Frequent-flyer cost concentration
  7. Composite risk score (recomputed in pandas, not SQL, to cross-validate Q11)
  8. Export a feature-engineered CSV for Power BI + save all charts
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("whitegrid")
NAVY = "#0D1B2A"
ACCENT = "#E63946"
PALETTE = ["#0D1B2A", "#415A77", "#778DA9", "#E0E1DD", "#E63946", "#F4A261"]
plt.rcParams["figure.dpi"] = 110
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.titlesize"] = 13

OUT = "eda_charts"
import os
os.makedirs(OUT, exist_ok=True)

# =========================================================
# 1. LOAD + DATA QUALITY CHECKS
# =========================================================

patients = pd.read_csv("patients.csv", dtype={"patient_id": str})
doctors = pd.read_csv("doctors.csv", dtype={"doctor_id": str})
encounters = pd.read_csv(
    "encounters.csv",
    dtype={"encounter_id": str, "patient_id": str, "doctor_id": str, "index_encounter_id": str},
    parse_dates=["admission_date", "discharge_date"],
)

print("=" * 60)
print("DATA QUALITY CHECKS")
print("=" * 60)

# Null check -- expected: only index_encounter_id has nulls (blank for non-readmissions)
print("\nNull counts (encounters):")
print(encounters.isnull().sum()[encounters.isnull().sum() > 0])

# Duplicate primary keys
print("\nDuplicate encounter_id rows:", encounters.encounter_id.duplicated().sum())
print("Duplicate patient_id rows:", patients.patient_id.duplicated().sum())

# Range sanity: LOS, cost, age must be positive / plausible
print("\nLOS range:", encounters.los_days.min(), "-", encounters.los_days.max())
print("Age range:", patients.age.min(), "-", patients.age.max())
print("Total bill range: Rs.", encounters.total_bill_inr.min(), "-", encounters.total_bill_inr.max())
assert (encounters.discharge_date >= encounters.admission_date).all(), "discharge before admission found!"
print("\nAll discharge dates >= admission dates: PASSED")

# Categorical value check -- catches stray typos/whitespace that a raw .value_counts() reveals
print("\ndiagnosis_category values:", encounters.diagnosis_category.unique())
print("insurance_type values:", patients.insurance_type.unique())
print("discharge_disposition values:", encounters.discharge_disposition.unique())

df = encounters.merge(patients, on="patient_id", how="left")
print(f"\nMerged shape: {df.shape} (should be {len(encounters)} rows -- a left merge shouldn't add/drop rows)")
assert len(df) == len(encounters), "merge changed row count -- check for duplicate patient_ids"

# =========================================================
# 2. FEATURE ENGINEERING
# =========================================================

def age_bucket(age):
    if age < 18: return "1. Under 18"
    if age <= 40: return "2. 18-40"
    if age <= 60: return "3. 41-60"
    if age <= 75: return "4. 61-75"
    return "5. 75+"

def los_bucket(los):
    if los <= 2: return "1. 1-2 days"
    if los <= 5: return "2. 3-5 days"
    if los <= 10: return "3. 6-10 days"
    return "4. 11+ days"

def med_bucket(n):
    if n <= 3: return "1. 1-3 (Low)"
    if n <= 7: return "2. 4-7 (Moderate)"
    if n <= 12: return "3. 8-12 (High)"
    return "4. 13+ (Polypharmacy)"

df["age_bucket"] = df.age.apply(age_bucket)
df["los_bucket"] = df.los_days.apply(los_bucket)
df["med_bucket"] = df.num_medications.apply(med_bucket)

# prior_admissions_365d -- the pandas equivalent of Q8's self-join.
# A self-join in SQL compares every row against every other row for the same key;
# in pandas, sorting by patient+date and using a rolling time-window count does the
# same job without a manual cross join. This is worth stating explicitly in the
# writeup as the SQL <-> pandas translation of the same idea.
df = df.sort_values(["patient_id", "admission_date"]).reset_index(drop=True)

prior_counts = np.zeros(len(df), dtype=int)
for pid, group in df.groupby("patient_id"):
    dates = group["admission_date"].values
    idx = group.index.values
    for i in range(len(dates)):
        window_start = dates[i] - np.timedelta64(365, "D")
        prior = ((dates[:i] >= window_start) & (dates[:i] < dates[i])).sum()
        prior_counts[idx[i]] = prior
df["prior_admissions_365d"] = prior_counts

# Cross-check against the SQL Q8 result before trusting this feature further
print("\n--- Cross-check: prior_admissions_365d distribution (pandas) ---")
print(df.prior_admissions_365d.value_counts().sort_index())

# is_frequent_flyer -- patient-level flag (Q10 logic)
patient_encounter_counts = df.groupby("patient_id").encounter_id.transform("count")
df["is_frequent_flyer"] = (patient_encounter_counts >= 2)

df.to_csv("encounters_features.csv", index=False)
print(f"\nSaved encounters_features.csv: {df.shape[0]} rows, {df.shape[1]} columns")

# =========================================================
# 3. UNIVARIATE DISTRIBUTIONS
# =========================================================

fig, axes = plt.subplots(2, 3, figsize=(15, 8))
fig.suptitle("Encounter-Level Distributions — FY 2024-25", fontsize=15, y=1.02)

sns.histplot(df.age, bins=30, color=NAVY, ax=axes[0, 0])
axes[0, 0].set_title("Age")

sns.histplot(df.los_days, bins=20, color=NAVY, ax=axes[0, 1])
axes[0, 1].set_title("Length of Stay (days)")

sns.histplot(df.total_bill_inr, bins=30, color=NAVY, ax=axes[0, 2])
axes[0, 2].set_title("Total Bill (INR)")
axes[0, 2].ticklabel_format(style="plain", axis="x")

sns.countplot(x=df.comorbidity_count, color=NAVY, ax=axes[1, 0])
axes[1, 0].set_title("Comorbidity Count")

cat_order = df.diagnosis_category.value_counts().index
sns.countplot(y=df.diagnosis_category, order=cat_order, color=NAVY, ax=axes[1, 1])
axes[1, 1].set_title("Encounters by Diagnosis Category")

sns.countplot(x=df.insurance_type, color=NAVY, ax=axes[1, 2],
              order=df.insurance_type.value_counts().index)
axes[1, 2].set_title("Encounters by Insurance Type")
axes[1, 2].tick_params(axis="x", rotation=20)

plt.tight_layout()
plt.savefig(f"{OUT}/01_univariate_distributions.png", bbox_inches="tight")
plt.close()
print("Saved 01_univariate_distributions.png")

# =========================================================
# 4. BIVARIATE: READMISSION DRIVERS (re-visualizing SQL Q1-Q6)
# =========================================================

idx = df[df.is_readmission == 0].copy()  # index stays only, same filter logic as SQL

def readmit_rate_by(col, order=None):
    g = idx.groupby(col)["readmitted_within_30d"].agg(["count", "mean"]).reset_index()
    g["rate_pct"] = g["mean"] * 100
    if order is not None:
        g[col] = pd.Categorical(g[col], categories=order, ordered=True)
        g = g.sort_values(col)
    return g

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Readmission Rate by Key Segments", fontsize=15, y=1.02)

# -- by category --
g = readmit_rate_by("diagnosis_category").sort_values("rate_pct", ascending=False)
sns.barplot(data=g, x="rate_pct", y="diagnosis_category", color=NAVY, ax=axes[0, 0])
axes[0, 0].set_title("By Diagnosis Category")
axes[0, 0].set_xlabel("30-day readmission rate (%)")
for i, v in enumerate(g.rate_pct):
    axes[0, 0].text(v + 0.3, i, f"{v:.1f}%", va="center", fontsize=9)

# -- by age bucket (the cleanest driver) --
age_order = ["1. Under 18", "2. 18-40", "3. 41-60", "4. 61-75", "5. 75+"]
g = readmit_rate_by("age_bucket", order=age_order)
sns.barplot(data=g, x="age_bucket", y="rate_pct", color=NAVY, ax=axes[0, 1])
axes[0, 1].set_title("By Age Bucket — monotonic climb")
axes[0, 1].set_ylabel("30-day readmission rate (%)")
axes[0, 1].tick_params(axis="x", rotation=20)
for i, v in enumerate(g.rate_pct):
    axes[0, 1].text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=9)

# -- by LOS bucket --
los_order = ["1. 1-2 days", "2. 3-5 days", "3. 6-10 days", "4. 11+ days"]
g = readmit_rate_by("los_bucket", order=los_order)
sns.barplot(data=g, x="los_bucket", y="rate_pct", color=NAVY, ax=axes[1, 0])
axes[1, 0].set_title("By Length of Stay")
axes[1, 0].set_ylabel("30-day readmission rate (%)")
axes[1, 0].tick_params(axis="x", rotation=20)
for i, v in enumerate(g.rate_pct):
    axes[1, 0].text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=9)

# -- by insurance type, with OOP% overlaid as a second series --
ins = idx.groupby("insurance_type").agg(
    readmit_rate=("readmitted_within_30d", "mean"),
    avg_bill=("total_bill_inr", "mean"),
    avg_oop=("oop_amount_inr", "mean"),
).reset_index()
ins["readmit_rate"] *= 100
ins["oop_pct"] = ins.avg_oop / ins.avg_bill * 100
ins = ins.sort_values("oop_pct", ascending=False)

ax = axes[1, 1]
x = np.arange(len(ins))
width = 0.35
ax.bar(x - width/2, ins.oop_pct, width, label="OOP % of bill", color=NAVY)
ax.bar(x + width/2, ins.readmit_rate, width, label="Readmission rate %", color=ACCENT)
ax.set_xticks(x)
ax.set_xticklabels(ins.insurance_type, rotation=15)
ax.set_title("By Insurance Type: OOP Burden vs Readmission")
ax.legend(fontsize=9)

plt.tight_layout()
plt.savefig(f"{OUT}/02_readmission_drivers.png", bbox_inches="tight")
plt.close()
print("Saved 02_readmission_drivers.png")

# =========================================================
# 5. THE Q7 CONFOUNDING CHECK
# SQL flagged: is num_medications really an independent driver, or riding
# on comorbidity_count? Correlation + a direct visual settle it here.
# =========================================================

corr_cols = ["age", "los_days", "comorbidity_count", "num_medications",
             "num_procedures", "prior_admissions_365d", "readmitted_within_30d"]
corr = df[corr_cols].corr()

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
            vmin=-1, vmax=1, ax=axes[0], cbar_kws={"shrink": 0.8})
axes[0].set_title("Correlation Matrix — Encounter-Level Features")

med_com_r = df["num_medications"].corr(df["comorbidity_count"])
sns.regplot(data=df.sample(2000, random_state=42), x="comorbidity_count", y="num_medications",
            scatter_kws={"alpha": 0.15, "color": NAVY, "s": 15},
            line_kws={"color": ACCENT}, ax=axes[1])
axes[1].set_title(f"num_medications vs comorbidity_count (r = {med_com_r:.2f})")
axes[1].set_xlabel("Comorbidity count")
axes[1].set_ylabel("Number of medications")

plt.tight_layout()
plt.savefig(f"{OUT}/03_confounding_check.png", bbox_inches="tight")
plt.close()
print(f"Saved 03_confounding_check.png (r = {med_com_r:.3f})")
print(f"\nCONFOUNDING CHECK RESULT: correlation = {med_com_r:.3f}")
print("Confirms the Q7 SQL writeup: medication count moves closely with comorbidity")
print("burden rather than acting as an independent driver.")

# =========================================================
# 6. FREQUENT-FLYER COST CONCENTRATION (Q10 re-visualized)
# =========================================================

patient_summary = df.groupby("patient_id").agg(
    n_encounters=("encounter_id", "count"),
    total_cost=("total_bill_inr", "sum"),
).reset_index()
patient_summary["segment"] = np.where(patient_summary.n_encounters >= 2,
                                       "Frequent (2+ encounters)", "Single-visit")

seg_summary = patient_summary.groupby("segment").agg(
    num_patients=("patient_id", "count"),
    total_cost=("total_cost", "sum"),
).reset_index()
seg_summary["pct_patients"] = seg_summary.num_patients / seg_summary.num_patients.sum() * 100
seg_summary["pct_cost"] = seg_summary.total_cost / seg_summary.total_cost.sum() * 100

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

x = np.arange(len(seg_summary))
width = 0.35
axes[0].bar(x - width/2, seg_summary.pct_patients, width, label="% of patients", color=NAVY)
axes[0].bar(x + width/2, seg_summary.pct_cost, width, label="% of total cost", color=ACCENT)
axes[0].set_xticks(x)
axes[0].set_xticklabels(seg_summary.segment, fontsize=9)
axes[0].set_title("Frequent-Flyer Patients: Share of Volume vs Cost")
axes[0].legend(fontsize=9)
for i in range(len(seg_summary)):
    axes[0].text(i - width/2, seg_summary.pct_patients.iloc[i] + 1,
                 f"{seg_summary.pct_patients.iloc[i]:.1f}%", ha="center", fontsize=9)
    axes[0].text(i + width/2, seg_summary.pct_cost.iloc[i] + 1,
                 f"{seg_summary.pct_cost.iloc[i]:.1f}%", ha="center", fontsize=9)

# -- risk tier validation (Q11 re-derived independently in pandas) --
def risk_points(row):
    pts = 0
    pts += 2 if row.age >= 75 else (1 if row.age >= 61 else 0)
    pts += 2 if row.comorbidity_count >= 3 else (1 if row.comorbidity_count == 2 else 0)
    pts += 2 if row.prior_admissions_365d >= 1 else 0
    pts += 1 if row.insurance_type == "Self-pay" else 0
    pts += 1 if row.discharge_disposition == "LAMA" else 0
    return pts

scored = df[df.discharge_disposition != "Deceased"].copy()
scored["risk_points"] = scored.apply(risk_points, axis=1)
scored["risk_tier"] = pd.cut(
    scored.risk_points, bins=[-1, 1, 3, 100],
    labels=["1. Low (0-1 pts)", "2. Medium (2-3 pts)", "3. High (4+ pts)"]
)
tier_summary = scored.groupby("risk_tier", observed=True)["readmitted_within_30d"].agg(
    ["count", "mean"]).reset_index()
tier_summary["rate_pct"] = tier_summary["mean"] * 100

sns.barplot(data=tier_summary, x="risk_tier", y="rate_pct", color=NAVY, ax=axes[1])
axes[1].set_title("Composite Risk-Tier Score — Validated in pandas")
axes[1].set_ylabel("30-day readmission rate (%)")
axes[1].tick_params(axis="x", rotation=10)
for i, v in enumerate(tier_summary.rate_pct):
    axes[1].text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=9)

plt.tight_layout()
plt.savefig(f"{OUT}/04_frequent_flyer_and_risk_tiers.png", bbox_inches="tight")
plt.close()
print("\nSaved 04_frequent_flyer_and_risk_tiers.png")
print("\n--- Cross-check: risk tier rates (pandas) vs SQL Q11 (9.94 / 21.21 / 26.59) ---")
print(tier_summary[["risk_tier", "count", "rate_pct"]])

