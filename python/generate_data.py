import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

# =========================================================
# REFERENCE DATA
# =========================================================

HOSPITAL_NAME = "Shanti Multispecialty Hospital, Gurugram"
YEAR_START = datetime(2024, 4, 1)   # Indian FY start
YEAR_END = datetime(2025, 3, 31)

DEPARTMENTS = {
    "Cardiovascular": "Cardiology",
    "Diabetes": "Endocrinology",
    "Respiratory": "Pulmonology",
    "CKD": "Nephrology",
    "Maternal_Neonatal": "Obstetrics & Gynaecology",
    "Surgical": "General Surgery",
}

ICD10 = {
    "Cardiovascular": [
        ("I50.9", "Heart failure, unspecified", 0.30),
        ("I25.10", "Chronic ischemic heart disease", 0.30),
        ("I11.0", "Hypertensive heart disease with heart failure", 0.22),
        ("I21.9", "Acute myocardial infarction, unspecified", 0.18),
    ],
    "Diabetes": [
        ("E11.9", "Type 2 diabetes mellitus without complications", 0.35),
        ("E11.22", "Type 2 diabetes with diabetic chronic kidney disease", 0.25),
        ("E11.52", "Type 2 diabetes with peripheral angiopathy", 0.22),
        ("E11.65", "Type 2 diabetes with hyperglycemia", 0.18),
    ],
    "Respiratory": [
        ("J44.1", "COPD with acute exacerbation", 0.38),
        ("J45.901", "Asthma exacerbation, unspecified", 0.30),
        ("J18.9", "Pneumonia, unspecified organism", 0.32),
    ],
    "CKD": [
        ("N18.3", "Chronic kidney disease, stage 3", 0.30),
        ("N18.4", "Chronic kidney disease, stage 4", 0.32),
        ("N18.5", "Chronic kidney disease, stage 5", 0.22),
        ("N18.6", "End stage renal disease", 0.16),
    ],
    "Maternal_Neonatal": [
        ("O80", "Normal vaginal delivery", 0.42),
        ("O82", "Delivery by caesarean section", 0.33),
        ("P07.3", "Preterm newborn, other", 0.13),
        ("Z38.00", "Single liveborn, born in hospital", 0.12),
    ],
    "Surgical": [
        ("K35.80", "Acute appendicitis", 0.30),
        ("K80.20", "Cholelithiasis with cholecystitis", 0.28),
        ("K40.90", "Inguinal hernia, unilateral", 0.24),
        ("S72.001A", "Fracture of femur, surgical repair", 0.18),
    ],
}

# Delhi-NCR core (tier-1, majority) + tier-2 referral catchment
CITIES_T1 = ["Gurugram", "Delhi", "Noida", "Faridabad", "Ghaziabad"]
CITIES_T2 = ["Meerut", "Rohtak", "Panipat", "Aligarh", "Alwar", "Bulandshahr"]
STATE_MAP = {
    "Gurugram": "Haryana", "Delhi": "Delhi", "Noida": "Uttar Pradesh",
    "Faridabad": "Haryana", "Ghaziabad": "Uttar Pradesh", "Meerut": "Uttar Pradesh",
    "Rohtak": "Haryana", "Panipat": "Haryana", "Aligarh": "Uttar Pradesh",
    "Alwar": "Rajasthan", "Bulandshahr": "Uttar Pradesh",
}

INSURANCE_TYPES = ["PMJAY", "Private Insurance", "CGHS", "Self-pay"]
INSURANCE_WEIGHTS = [0.35, 0.25, 0.08, 0.32]
# coverage fraction of bill paid by insurer (rest = OOP)
COVERAGE = {"PMJAY": (0.95, 1.00), "CGHS": (0.85, 0.95),
            "Private Insurance": (0.55, 0.85), "Self-pay": (0.0, 0.0)}

MALE_FIRST = ["Rohan","Amit","Vikram","Suresh","Rajesh","Manoj","Ankit","Deepak",
              "Sanjay","Arvind","Ramesh","Vivek","Anil","Pankaj","Sandeep","Naveen",
              "Ashok","Ravi","Yogesh","Harish","Mohit","Gaurav","Prakash","Sunil"]
FEMALE_FIRST = ["Priya","Sunita","Anjali","Kavita","Neha","Pooja","Rekha","Meera",
                "Sarita","Anita","Deepika","Nisha","Shalini","Geeta","Kiran","Ritu",
                "Swati","Vandana","Alka","Manju","Shweta","Poonam","Usha","Renu"]
LAST_NAMES = ["Sharma","Verma","Singh","Kumar","Gupta","Yadav","Chauhan","Mishra",
              "Tyagi","Jain","Malik","Rathi","Choudhary","Tomar","Bansal","Agarwal",
              "Saxena","Pandey","Rawat","Chopra"]

DOCTOR_FIRST = MALE_FIRST + FEMALE_FIRST
DESIGNATIONS = ["Senior Consultant", "Consultant", "Associate Consultant", "Resident"]

def indian_name(gender):
    first = random.choice(MALE_FIRST if gender == "M" else FEMALE_FIRST)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"

def pick_city():
    if random.random() < 0.72:
        c = random.choice(CITIES_T1)
        tier = "Tier-1"
    else:
        c = random.choice(CITIES_T2)
        tier = "Tier-2"
    return c, STATE_MAP[c], tier

# =========================================================
# DOCTORS
# =========================================================
doctors = []
doc_id = 1
for cat, dept in DEPARTMENTS.items():
    n_docs = random.randint(6, 9)
    for _ in range(n_docs):
        gender = random.choice(["M", "F"])
        exp = int(np.clip(np.random.exponential(8) + 1, 1, 35))
        desig = "Senior Consultant" if exp > 15 else ("Consultant" if exp > 7 else
                 ("Associate Consultant" if exp > 3 else "Resident"))
        doctors.append({
            "doctor_id": f"D{doc_id:03d}",
            "doctor_name": ("Dr. " + indian_name(gender)),
            "department": dept,
            "designation": desig,
            "years_experience": exp,
        })
        doc_id += 1
doctors_df = pd.DataFrame(doctors)

def doctor_for_dept(dept):
    pool = doctors_df[doctors_df.department == dept].doctor_id.values
    return random.choice(pool)

print(f"Doctors generated: {len(doctors_df)}")
doctors_df.to_csv("doctors.csv", index=False)

# =========================================================
# CATEGORY CONFIG: age ranges, LOS, cost, base readmission rate
# =========================================================

CATEGORY_WEIGHTS = {
    "Cardiovascular": 0.24,
    "Diabetes": 0.19,
    "Respiratory": 0.17,
    "Maternal_Neonatal": 0.18,
    "CKD": 0.11,
    "Surgical": 0.11,
}

# (age_mean, age_sd, age_min, age_max)
AGE_PROFILE = {
    "Cardiovascular": (63, 12, 35, 92),
    "Diabetes": (56, 11, 30, 88),
    "Respiratory": (52, 18, 18, 90),
    "CKD": (57, 13, 25, 88),
    "Maternal_Neonatal": (27, 5, 17, 42),
    "Surgical": (44, 16, 12, 85),
}

LOS_PROFILE = {
    "Cardiovascular": (2.2, 1.8, 2),
    "Diabetes": (1.8, 1.5, 1),
    "Respiratory": (2.0, 1.7, 2),
    "CKD": (2.5, 2.0, 2),
    "Maternal_Neonatal": (1.3, 1.0, 1),
    "Surgical": (2.0, 1.6, 1),
}

COST_PROFILE = {
    "Cardiovascular": (95000, 5500, 9000),
    "Diabetes": (22000, 2000, 5000),
    "Respiratory": (18000, 1800, 4000),
    "CKD": (65000, 5500, 6000),
    "Maternal_Neonatal": (18000, 1600, 13000),
    "Surgical": (42000, 5200, 10500),
}

BASE_READMIT_RATE = {
    "Cardiovascular": 0.235,
    "Diabetes": 0.195,
    "Respiratory": 0.185,
    "CKD": 0.255,
    "Maternal_Neonatal": 0.055,
    "Surgical": 0.095,
}

RESP_SEASON = {1:1.7, 2:1.5, 3:1.0, 4:0.7, 5:0.6, 6:0.9, 7:1.1, 8:1.1,
               9:0.8, 10:1.3, 11:1.8, 12:1.9}

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def sample_age(cat):
    mean, sd, lo, hi = AGE_PROFILE[cat]
    a = int(np.clip(np.random.normal(mean, sd), lo, hi))
    return a

def sample_los(cat):
    shape, scale, minimum = LOS_PROFILE[cat]
    return int(np.clip(round(np.random.gamma(shape, scale)) + minimum, 1, 30))

def sample_comorbidity(age, cat):
    chronic = cat in ("Cardiovascular", "Diabetes", "CKD")
    base = 0.5 + (age / 100) * 2.0 + (1.2 if chronic else 0)
    return int(np.clip(np.random.poisson(base), 0, 5))

def sample_medications(age, comorbidity, cat):
    chronic = cat in ("Cardiovascular", "Diabetes", "CKD")
    base = 3 + comorbidity * 1.8 + (age / 100) * 3 + (2 if chronic else 0)
    return int(np.clip(np.random.poisson(base), 1, 20))

def sample_procedures(cat):
    if cat == "Surgical":
        return 1 + np.random.poisson(0.6)
    if cat == "Maternal_Neonatal":
        return int(np.random.rand() < 0.4)
    return np.random.poisson(0.5)

def assign_insurance():
    return np.random.choice(INSURANCE_TYPES, p=INSURANCE_WEIGHTS)

def sample_discharge_disposition(cat, insurance, age):
    p_death = {"Cardiovascular": 0.035, "Diabetes": 0.01, "Respiratory": 0.025,
               "CKD": 0.03, "Maternal_Neonatal": 0.004, "Surgical": 0.008}[cat]
    p_lama = 0.08 if insurance == "Self-pay" else 0.03
    p_transfer = 0.02
    p_routine = max(0.0, 1 - p_death - p_lama - p_transfer)
    return np.random.choice(
        ["Routine", "LAMA", "Transferred", "Deceased"],
        p=[p_routine, p_lama, p_transfer, p_death]
    )

def sample_cost(cat, los, n_proc):
    base, per_day, per_proc = COST_PROFILE[cat]
    noise = np.random.normal(1.0, 0.12)
    cost = (base + per_day * los + per_proc * n_proc) * max(noise, 0.6)
    return round(cost, -2)

def coverage_fraction(insurance):
    lo, hi = COVERAGE[insurance]
    if lo == hi:
        return lo
    return np.random.uniform(lo, hi)

def random_date_in_year():
    days = (YEAR_END - YEAR_START).days
    return YEAR_START + timedelta(days=random.randint(0, days))

def seasonal_index_date(cat):
    """Pick an admission date; respiratory is seasonally weighted."""
    if cat != "Respiratory":
        return random_date_in_year()
    # weighted month sampling across the FY (Apr..Mar)
    months = list(range(1, 13))
    weights = np.array([RESP_SEASON[m] for m in months], dtype=float)
    weights /= weights.sum()
    month = np.random.choice(months, p=weights)
    year = 2024 if month >= 4 else 2025
    day = random.randint(1, 28)
    return datetime(year, month, day)

# =========================================================
# MAIN SIMULATION
# =========================================================

N_INDEX = 7500
MAX_CHAIN = 3
FREQUENT_FLYER_BOOST = 1.35

patients = []
encounters = []
patient_seq = 1
encounter_seq = 1

def new_patient(cat):
    global patient_seq
    if cat == "Maternal_Neonatal":
        is_neonate = random.random() < 0.30
        gender = "F" if not is_neonate else random.choice(["M", "F"])
        age = 0 if is_neonate else sample_age(cat)
    else:
        gender = random.choice(["M", "F"])
        age = sample_age(cat)
    city, state, tier = pick_city()
    insurance = assign_insurance()
    pid = f"P{patient_seq:05d}"
    patients.append({
        "patient_id": pid,
        "patient_name": indian_name(gender) if age > 0 else (indian_name(gender) + " (Infant)"),
        "gender": gender,
        "age": age,
        "city": city,
        "state": state,
        "city_tier": tier,
        "insurance_type": insurance,
    })
    patient_seq += 1
    return patients[-1]

def make_encounter(patient, cat, admission_date, index_encounter_id=None, chain_no=0):
    global encounter_seq
    los = sample_los(cat)
    # readmission encounters tend to run a bit longer/sicker
    if chain_no > 0:
        los = int(np.clip(los + np.random.poisson(1), 1, 30))
    discharge_date = admission_date + timedelta(days=los)
    comorbidity = sample_comorbidity(patient["age"], cat)
    meds = sample_medications(patient["age"], comorbidity, cat)
    n_proc = sample_procedures(cat)
    disposition = sample_discharge_disposition(cat, patient["insurance_type"], patient["age"])
    cost = sample_cost(cat, los, n_proc)
    coverage = coverage_fraction(patient["insurance_type"])
    oop = round(cost * (1 - coverage), -1)
    icd_choices = ICD10[cat]
    codes, descs, wts = zip(*icd_choices)
    idx = np.random.choice(len(codes), p=np.array(wts) / sum(wts))
    dept = DEPARTMENTS[cat]
    doc = doctor_for_dept(dept)

    eid = f"E{encounter_seq:06d}"
    encounter_seq += 1
    row = {
        "encounter_id": eid,
        "patient_id": patient["patient_id"],
        "doctor_id": doc,
        "department": dept,
        "diagnosis_category": cat,
        "icd10_code": codes[idx],
        "icd10_description": descs[idx],
        "admission_date": admission_date.date().isoformat(),
        "discharge_date": discharge_date.date().isoformat(),
        "los_days": los,
        "comorbidity_count": comorbidity,
        "num_medications": meds,
        "num_procedures": n_proc,
        "discharge_disposition": disposition,
        "total_bill_inr": cost,
        "oop_amount_inr": oop,
        "is_readmission": 1 if index_encounter_id else 0,
        "index_encounter_id": index_encounter_id if index_encounter_id else "",
        "readmitted_within_30d": 0,   # filled in after we know if a chain follows
    }
    encounters.append(row)
    return row, comorbidity, meds, disposition

def readmit_probability(cat, age, comorbidity, meds, los, insurance, disposition):
    base = BASE_READMIT_RATE[cat]
    z = np.log(base / (1 - base))

    # Center every adjustment on THIS category's actual expected average,
    # not a fixed constant -- otherwise "chronic" categories look
    # universally high-risk instead of having real above/below-average spread.
    age_mean = AGE_PROFILE[cat][0]
    chronic = cat in ("Cardiovascular", "Diabetes", "CKD")
    comorbidity_mean = 0.5 + (age_mean / 100) * 2.0 + (1.2 if chronic else 0)
    meds_mean = 3 + comorbidity_mean * 1.8 + (age_mean / 100) * 3 + (2 if chronic else 0)
    los_mean = LOS_PROFILE[cat][0] * LOS_PROFILE[cat][1] + LOS_PROFILE[cat][2]

    z += 0.012 * (age - age_mean)
    z += 0.16 * (comorbidity - comorbidity_mean)
    z += 0.05 * (meds - meds_mean)
    z += 0.06 * (los - los_mean)
    if insurance == "Self-pay":
        z += 0.20
    if insurance == "PMJAY":
        z += 0.04
    if disposition == "LAMA":
        z += 0.30
    if disposition == "Deceased":
        return 0.0
    p = sigmoid(z)
    return float(np.clip(p, 0.01, 0.85))

# ---- generate index admissions ----
cats = list(CATEGORY_WEIGHTS.keys())
cat_probs = list(CATEGORY_WEIGHTS.values())
index_cats = np.random.choice(cats, size=N_INDEX, p=cat_probs)

for cat in index_cats:
    patient = new_patient(cat)
    adm_date = seasonal_index_date(cat)
    row, comorbidity, meds, disposition = make_encounter(patient, cat, adm_date)

    chain_no = 0
    current_row = row
    current_comorbidity, current_meds, current_disposition = comorbidity, meds, disposition
    last_discharge = datetime.fromisoformat(current_row["discharge_date"])

    # frequent-flyer boost: elderly + multi-comorbid chronic patients chain more
    is_chronic_elderly = (cat in ("Cardiovascular", "CKD", "Diabetes")
                           and patient["age"] >= 70 and current_comorbidity >= 4)

    while chain_no < MAX_CHAIN - 1:
        p_readmit = readmit_probability(
            cat, patient["age"], current_comorbidity, current_meds,
            current_row["los_days"], patient["insurance_type"], current_disposition
        )
        if is_chronic_elderly:
            p_readmit = min(0.9, p_readmit * FREQUENT_FLYER_BOOST)

        if np.random.rand() < p_readmit and last_discharge < YEAR_END - timedelta(days=3):
            gap_days = random.randint(3, 30)
            next_adm = last_discharge + timedelta(days=gap_days)
            if next_adm > YEAR_END:
                break
            current_row["readmitted_within_30d"] = 1
            prior_encounter_id = current_row["encounter_id"]
            next_row, next_com, next_meds, next_disp = make_encounter(
                patient, cat, next_adm, index_encounter_id=prior_encounter_id,
                chain_no=chain_no + 1
            )
            current_row = next_row
            current_comorbidity, current_meds, current_disposition = next_com, next_meds, next_disp
            last_discharge = datetime.fromisoformat(current_row["discharge_date"])
            chain_no += 1
        else:
            break

patients_df = pd.DataFrame(patients)
encounters_df = pd.DataFrame(encounters)

patients_df.to_csv("patients.csv", index=False)
encounters_df.to_csv("encounters.csv", index=False)

print(f"Patients: {len(patients_df)}")
print(f"Encounters: {len(encounters_df)}")
print(f"Overall 30-day readmission rate: {encounters_df['readmitted_within_30d'].mean():.3f}")
print("\nReadmission rate by category (index/original encounters only):")
idx_only = encounters_df[encounters_df.is_readmission == 0]
print(idx_only.groupby("diagnosis_category")["readmitted_within_30d"].mean().round(3))
print("\nEncounters by category:")
print(encounters_df["diagnosis_category"].value_counts())
print("\nInsurance mix:")
print(patients_df["insurance_type"].value_counts(normalize=True).round(3))
print("\nDischarge disposition mix:")
print(encounters_df["discharge_disposition"].value_counts(normalize=True).round(3))
