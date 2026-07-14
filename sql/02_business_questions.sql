/* ============================================================
   HOSPITAL READMISSION & PATIENT FLOW ANALYTICS
   Shanti Multispecialty Hospital, Gurugram | FY 2024-25
   Consolidated Business-Question SQL Script
   Tables: patients | doctors | encounters
   ============================================================
   NOTE ON DATA TYPES: encounter_id, patient_id, doctor_id, and
   index_encounter_id must be imported as VARCHAR (not numeric/
   auto-detected). If IDs ever display as "1.00" instead of
   "E000001", the CSV was likely opened/saved in Excel/Sheets,
   which silently strips prefixes and reformats them as numbers.
   Always view/edit these CSVs in Notepad, never Excel, before
   importing.

   NOTE ON BIT COLUMNS: readmitted_within_30d and is_readmission
   import as SQL Server's BIT type (since they're only ever 0/1).
   BIT cannot be used directly inside SUM() or other arithmetic --
   it must be CAST to INT first. Every query below already does
   this; keep the pattern if you write new queries against these
   columns.
   ============================================================ */


/* ============================================================
   Q1. OVERALL READMISSION RATE BY DIAGNOSIS CATEGORY
   Business question: what % of discharges bounce back within 30
   days, and which specialty drives that number up? (Executive
   Overview headline metric)
   ============================================================ */

-- FROM: encounters (each row = one hospital stay)
-- JOIN ON: none needed -- everything lives on the encounters table
-- WHERE: exclude readmission rows themselves from the denominator --
--        we only want to ask "of patients DISCHARGED as an index
--        stay, how many came back?" A readmission row can't be
--        judged on whether IT caused a readmission the same way.
-- SELECT: category, total qualifying discharges, how many were
--        readmitted within 30 days, and the rate

SELECT
    diagnosis_category,
    COUNT(*)                                                AS total_discharges,
    SUM(CAST(readmitted_within_30d AS INT))                 AS readmitted_count,
    CAST(SUM(CAST(readmitted_within_30d AS INT)) AS FLOAT)
        / COUNT(*) * 100                                    AS readmission_rate_pct
FROM encounters
WHERE is_readmission = 0
GROUP BY diagnosis_category
ORDER BY readmission_rate_pct DESC;


/* ============================================================
   Q2. AGE-BUCKET RISK SEGMENTATION
   Business question: at what age does readmission risk actually
   start climbing, so discharge planning can flag patients above
   that threshold for extra follow-up?
   ============================================================ */

-- FROM: patients joined to encounters, since age lives on patients
--       but readmission outcome lives on encounters
-- JOIN ON: patient_id -- every encounter belongs to exactly one patient
-- WHERE: only index stays (same reasoning as Q1)
-- SELECT: bucket patients into age bands using CASE WHEN, then
--        compute readmission rate per band
-- NOTE: CASE WHEN is repeated in GROUP BY because SQL Server does
--       NOT allow grouping by a SELECT alias (unlike Postgres/MySQL)
-- NOTE: numeric prefixes ('1. ', '2. ') on labels force correct
--       logical sort order instead of alphabetical

SELECT
    CASE
        WHEN p.age < 18                  THEN '1. Under 18 (Pediatric/Neonatal)'
        WHEN p.age BETWEEN 18 AND 40      THEN '2. 18-40'
        WHEN p.age BETWEEN 41 AND 60      THEN '3. 41-60'
        WHEN p.age BETWEEN 61 AND 75      THEN '4. 61-75'
        ELSE                                   '5. 75+'
    END                                                       AS age_bucket,
    COUNT(*)                                                  AS total_discharges,
    SUM(CAST(e.readmitted_within_30d AS INT))                 AS readmitted_count,
    CAST(SUM(CAST(e.readmitted_within_30d AS INT)) AS FLOAT)
        / COUNT(*) * 100                                      AS readmission_rate_pct
FROM patients AS p
JOIN encounters AS e
    ON p.patient_id = e.patient_id
WHERE e.is_readmission = 0
GROUP BY
    CASE
        WHEN p.age < 18                  THEN '1. Under 18 (Pediatric/Neonatal)'
        WHEN p.age BETWEEN 18 AND 40      THEN '2. 18-40'
        WHEN p.age BETWEEN 41 AND 60      THEN '3. 41-60'
        WHEN p.age BETWEEN 61 AND 75      THEN '4. 61-75'
        ELSE                                   '5. 75+'
    END
ORDER BY age_bucket;


/* ============================================================
   Q3. LENGTH OF STAY (LOS) VS READMISSION AND COST
   Business question: do shorter stays (discharged before stable)
   or longer stays (sicker to begin with) show higher readmission?
   Bonus: does LOS also predict cost, strengthening the case for
   investing in discharge planning for extended stays?
   ============================================================ */

-- FROM: encounters (LOS, readmission, and cost all live here -- no join)
-- WHERE: only index stays
-- SELECT: bucket LOS, compute readmission rate AND avg cost per band
-- NOTE: order matters in a CASE WHEN chain -- SQL evaluates top to
--       bottom and stops at the first true condition, so each WHEN
--       only needs an upper bound (falls through if not matched)

SELECT
    CASE
        WHEN los_days <= 2   THEN '1. 1-2 days (Short stay)'
        WHEN los_days <= 5   THEN '2. 3-5 days'
        WHEN los_days <= 10  THEN '3. 6-10 days'
        ELSE                      '4. 11+ days (Extended stay)'
    END                                                    AS los_bucket,
    COUNT(*)                                               AS total_discharges,
    SUM(CAST(readmitted_within_30d AS INT))                AS readmitted_count,
    CAST(SUM(CAST(readmitted_within_30d AS INT)) AS FLOAT)
        / COUNT(*) * 100                                   AS readmission_rate_pct,
    AVG(total_bill_inr)                                    AS avg_bill_inr
FROM encounters
WHERE is_readmission = 0
GROUP BY
    CASE
        WHEN los_days <= 2   THEN '1. 1-2 days (Short stay)'
        WHEN los_days <= 5   THEN '2. 3-5 days'
        WHEN los_days <= 10  THEN '3. 6-10 days'
        ELSE                      '4. 11+ days (Extended stay)'
    END
ORDER BY los_bucket;


/* ============================================================
   Q4. COST / OUT-OF-POCKET BURDEN BY INSURANCE TYPE
   Business question: the equity/access angle -- how unevenly is
   OOP burden distributed, and does payment type correlate with
   readmission risk?
   ============================================================ */

-- FROM: patients joined to encounters, since insurance_type lives
--       on patients but cost/readmission outcome live on encounters
-- JOIN ON: patient_id
-- WHERE: only index stays
-- SELECT: insurance type, avg bill, avg OOP, OOP as % of bill,
--        readmission rate
-- NOTE: oop_pct_of_bill is a RATIO OF AVERAGES
--       (AVG(oop)/AVG(bill)), not an AVERAGE OF RATIOS
--       (AVG(oop/bill)) -- these are NOT the same number in
--       general. Ratio-of-averages answers "of all money spent by
--       this group, what fraction was OOP" -- the right aggregate
--       question here.

SELECT
    p.insurance_type,
    COUNT(*)                                                  AS total_discharges,
    AVG(e.total_bill_inr)                                     AS avg_bill_inr,
    AVG(e.oop_amount_inr)                                     AS avg_oop_inr,
    CAST(AVG(e.oop_amount_inr) AS FLOAT)
        / AVG(e.total_bill_inr) * 100                         AS oop_pct_of_bill,
    SUM(CAST(e.readmitted_within_30d AS INT))                 AS readmitted_count,
    CAST(SUM(CAST(e.readmitted_within_30d AS INT)) AS FLOAT)
        / COUNT(*) * 100                                      AS readmission_rate_pct
FROM patients AS p
JOIN encounters AS e
    ON p.patient_id = e.patient_id
WHERE e.is_readmission = 0
GROUP BY p.insurance_type
ORDER BY oop_pct_of_bill DESC;


/* ============================================================
   Q5a. DEPARTMENT-LEVEL READMISSION RATES
   Q5b. DOCTOR-LEVEL READMISSION RATES
   Business question: is readmission risk evenly spread across
   departments/doctors, or concentrated?
   LIMITATION (be upfront about this in interviews): doctor_id was
   never fed into the underlying readmission risk model -- it was
   only used to assign a plausible department. Any doctor-level
   variance seen below is sampling noise, not a real signal. A real
   hospital dataset would likely show genuine physician-level
   variance; this is a modeling gap worth naming as future work.
   ============================================================ */

-- Q5a: department level
-- FROM: encounters joined to doctors (department info lives on doctors)
-- JOIN ON: doctor_id
-- WHERE: only index stays
-- HAVING: defensive filter -- excludes groups with too few cases to
--        be meaningful (doesn't change this result, since every
--        department has hundreds of cases, but is the correct habit,
--        and becomes essential in the doctor-level version below)

SELECT
    d.department,
    COUNT(DISTINCT d.doctor_id)                               AS num_doctors,
    COUNT(*)                                                  AS total_discharges,
    SUM(CAST(e.readmitted_within_30d AS INT))                 AS readmitted_count,
    CAST(SUM(CAST(e.readmitted_within_30d AS INT)) AS FLOAT)
        / COUNT(*) * 100                                      AS readmission_rate_pct
FROM encounters AS e
JOIN doctors AS d
    ON e.doctor_id = d.doctor_id
WHERE e.is_readmission = 0
GROUP BY d.department
HAVING COUNT(*) >= 50
ORDER BY readmission_rate_pct DESC;

-- Q5b: doctor level -- HAVING matters more here, since individual
--      doctors can have small case counts where a couple of chance
--      readmissions would otherwise look like a "high risk doctor"

SELECT
    d.doctor_id,
    d.doctor_name,
    d.department,
    d.designation,
    COUNT(*)                                                  AS total_discharges,
    SUM(CAST(e.readmitted_within_30d AS INT))                 AS readmitted_count,
    CAST(SUM(CAST(e.readmitted_within_30d AS INT)) AS FLOAT)
        / COUNT(*) * 100                                      AS readmission_rate_pct
FROM encounters AS e
JOIN doctors AS d
    ON e.doctor_id = d.doctor_id
WHERE e.is_readmission = 0
GROUP BY d.doctor_id, d.doctor_name, d.department, d.designation
HAVING COUNT(*) >= 30
ORDER BY readmission_rate_pct DESC;


/* ============================================================
   Q6. DISCHARGE DISPOSITION IMPACT ON READMISSION
   Business question: the most operationally actionable finding --
   do patients who leave "Against Medical Advice" (LAMA) show
   higher readmission? If so, that's a fixable process issue
   (pre-discharge counseling, follow-up calls), not just a
   demographic fact.
   RESULT NOTE: the effect is real but modest (~22.5% LAMA vs
   ~17.6% Routine, a ~28% RELATIVE increase) -- describe it as "a
   consistent elevation," not a dramatic outlier, if asked.
   ============================================================ */

-- FROM: encounters (disposition and readmission outcome both live here)
-- WHERE: only index stays, AND exclude Deceased -- a deceased
--        patient cannot be readmitted by definition, so leaving
--        them in would misleadingly show a mechanical "0% readmission"
--        for that group, which isn't a real clinical outcome

SELECT
    discharge_disposition,
    COUNT(*)                                               AS total_discharges,
    SUM(CAST(readmitted_within_30d AS INT))                AS readmitted_count,
    CAST(SUM(CAST(readmitted_within_30d AS INT)) AS FLOAT)
        / COUNT(*) * 100                                   AS readmission_rate_pct
FROM encounters
WHERE is_readmission = 0
  AND discharge_disposition <> 'Deceased'
GROUP BY discharge_disposition
ORDER BY readmission_rate_pct DESC;


/* ============================================================
   Q7. MEDICATION COMPLEXITY VS READMISSION
   Business question: does polypharmacy (many medications) predict
   readmission, as it does in real-world literature?
   RESULT NOTE / CONFOUNDING: num_medications is generated FROM
   comorbidity_count (large multiplier) plus age and category, and
   comorbidity_count has the single largest coefficient in the
   underlying risk model. So medication count is likely acting as a
   PROXY for comorbidity burden, not an independent driver. Say so
   explicitly: "medication complexity is a strong indicator, but
   likely proxies underlying comorbidity burden rather than acting
   as an independent causal driver." Verify with a correlation
   check between num_medications and comorbidity_count in Python.
   ============================================================ */

SELECT
    CASE
        WHEN num_medications <= 3   THEN '1. 1-3 (Low complexity)'
        WHEN num_medications <= 7   THEN '2. 4-7 (Moderate)'
        WHEN num_medications <= 12  THEN '3. 8-12 (High)'
        ELSE                             '4. 13+ (Very high / polypharmacy)'
    END                                                    AS medication_bucket,
    COUNT(*)                                               AS total_discharges,
    SUM(CAST(readmitted_within_30d AS INT))                AS readmitted_count,
    CAST(SUM(CAST(readmitted_within_30d AS INT)) AS FLOAT)
        / COUNT(*) * 100                                   AS readmission_rate_pct
FROM encounters
WHERE is_readmission = 0
GROUP BY
    CASE
        WHEN num_medications <= 3   THEN '1. 1-3 (Low complexity)'
        WHEN num_medications <= 7   THEN '2. 4-7 (Moderate)'
        WHEN num_medications <= 12  THEN '3. 8-12 (High)'
        ELSE                             '4. 13+ (Very high / polypharmacy)'
    END
ORDER BY medication_bucket;


/* ============================================================
   Q8. PRIOR ADMISSION COUNT PER PATIENT (SELF-JOIN)
   Business question: "has this patient been in before?" -- one of
   the strongest real-world hospital risk signals. Requires
   comparing each encounter against OTHER rows for the SAME
   patient -- a self-join.
   IMPORTANT STRUCTURAL NOTE: do NOT filter to is_readmission = 0
   here. Every is_readmission = 0 row is, by construction, that
   patient's very first encounter -- so prior_admissions_365d would
   always be 0 if filtered that way (this was an actual mistake
   caught during development -- see below). We want prior-admission
   count for EVERY encounter, since a readmission encounter can
   still have its own further history.
   ============================================================ */

-- FROM: encounters e1 (the "current" encounter being evaluated)
-- JOIN ON: encounters e2 (a second copy of the SAME table), same
--         patient_id, where e2 was admitted BEFORE e1 and within
--         the trailing 365 days
-- WHERE: none -- computed for every encounter
-- SELECT: for each encounter, count how many prior e2 rows exist

SELECT
    e1.encounter_id,
    e1.patient_id,
    e1.admission_date,
    e1.diagnosis_category,
    e1.is_readmission,
    COUNT(e2.encounter_id)                                 AS prior_admissions_365d,
    e1.readmitted_within_30d
FROM encounters AS e1
LEFT JOIN encounters AS e2                                 -- LEFT, not INNER --
    ON e1.patient_id = e2.patient_id                       -- otherwise patients
    AND e2.admission_date < e1.admission_date              -- with 0 prior visits
    AND e2.admission_date >= DATEADD(DAY, -365, e1.admission_date)  -- would vanish
GROUP BY
    e1.encounter_id, e1.patient_id, e1.admission_date,
    e1.diagnosis_category, e1.is_readmission, e1.readmitted_within_30d
ORDER BY prior_admissions_365d DESC;


/* ============================================================
   Q9. DAYS SINCE LAST DISCHARGE (WINDOW FUNCTION -- LAG())
   Business question: proves the readmission label is real, row by
   row -- shows the actual day-gap between a patient's discharge
   and their next admission.
   WHEN TO USE LAG() VS A SELF-JOIN: one row of context needed
   (the row right before this one) -> window function. Many rows
   of context needed (count across a date range) -> self-join
   (see Q8). Recognizing this distinction is worth being able to
   explain out loud.
   ============================================================ */

-- FROM: encounters (every row)
-- JOIN ON: none needed -- LAG() looks sideways at neighboring rows
--         within a defined ordering, no self-join required
-- PARTITION BY patient_id: resets "previous row" logic separately
--         per patient -- without this, LAG() would pull the
--         previous discharge date from whatever patient happens to
--         sit one row above in raw table order, which is meaningless
-- ORDER BY admission_date (inside OVER): defines what "previous"
--         means -- without it, "previous row" is undefined

SELECT
    encounter_id,
    patient_id,
    diagnosis_category,
    admission_date,
    LAG(discharge_date) OVER (
        PARTITION BY patient_id
        ORDER BY admission_date
    )                                                       AS previous_discharge_date,
    DATEDIFF(
        DAY,
        LAG(discharge_date) OVER (
            PARTITION BY patient_id
            ORDER BY admission_date
        ),
        admission_date
    )                                                       AS days_since_last_discharge,
    is_readmission,
    readmitted_within_30d
FROM encounters
ORDER BY patient_id, admission_date;

-- Single-patient proof-of-concept version (swap in any patient_id
-- that showed prior_admissions_365d >= 1 in the Q8 output):

-- SELECT
--     encounter_id, patient_id, diagnosis_category,
--     admission_date, discharge_date,
--     LAG(discharge_date) OVER (PARTITION BY patient_id ORDER BY admission_date) AS previous_discharge_date,
--     DATEDIFF(DAY, LAG(discharge_date) OVER (PARTITION BY patient_id ORDER BY admission_date), admission_date) AS days_since_last_discharge,
--     is_readmission, readmitted_within_30d
-- FROM encounters
-- WHERE patient_id = 'P00175'          -- must match VARCHAR format, e.g. 'P00175' not 175
-- ORDER BY admission_date;


/* ============================================================
   Q10. FREQUENT-FLYER SEGMENT: SHARE OF COST/BED-DAYS VS SHARE
        OF PATIENT VOLUME
   Business question: the "small % of patients drive disproportionate
   cost" story -- turns a patient-count fact into a resource-
   allocation argument.
   RESULT: ~17.5% of patients (2+ encounters/year) account for
   ~37.4% of total cost -- more than double their proportional share.
   ============================================================ */

-- STEP 1 (CTE): collapse to one row per patient with their totals
-- STEP 2: classify Frequent (2+) vs Single-visit, then compare
--        each segment's share of patient count vs share of cost
-- NOTE: SUM(COUNT(*)) OVER () is a window function stacked on an
--       aggregate -- COUNT(*) gives per-segment counts (2 rows),
--       OVER () with no PARTITION BY computes the grand total
--       across ALL rows without collapsing the 2 segment rows into
--       one. This is the standard trick for "% of total" columns
--       on a dashboard, worth remembering by name.

WITH patient_summary AS (
    SELECT
        patient_id,
        COUNT(*)                       AS total_encounters,
        SUM(los_days)                  AS total_bed_days,
        SUM(total_bill_inr)            AS total_cost_inr,
        CASE
            WHEN COUNT(*) >= 2 THEN 'Frequent (2+ encounters)'
            ELSE 'Single-visit'
        END                             AS patient_segment
    FROM encounters
    GROUP BY patient_id
)
SELECT
    patient_segment,
    COUNT(*)                                                      AS num_patients,
    CAST(COUNT(*) AS FLOAT)
        / SUM(COUNT(*)) OVER () * 100                             AS pct_of_all_patients,
    SUM(total_encounters)                                         AS total_encounters,
    SUM(total_bed_days)                                           AS total_bed_days,
    SUM(total_cost_inr)                                           AS total_cost_inr,
    CAST(SUM(total_cost_inr) AS FLOAT)
        / SUM(SUM(total_cost_inr)) OVER () * 100                  AS pct_of_all_cost
FROM patient_summary
GROUP BY patient_segment;


/* ============================================================
   Q11. COMPOSITE RISK-TIER SCORE (CAPSTONE QUERY)
   Business question: ties everything together -- a single
   transparent, point-based risk score (age + comorbidity + prior
   admissions + insurance + discharge disposition), bucketed into
   Low/Medium/High tiers, validated against real readmission rates.
   IMPORTANT: this is a RULE-BASED heuristic, not a fitted model.
   The point weights are a judgment call, not statistically derived.
   Say so explicitly: "a natural next step would be a logistic
   regression in Python to let the data determine each factor's
   actual weight, rather than an assigned one."
   RESULT NOTE: Low 9.9% -> Medium 21.2% -> High 26.6%. Most of the
   separating power is between Low and Medium; Medium-to-High barely
   moves. Fair interpretation: the score is good at flagging "some
   real risk factor is present" but doesn't strongly differentiate
   WITHIN the elevated-risk group in this rule-based version.
   ============================================================ */

-- STEP 1 (CTE): reuse the Q8 self-join logic, across ALL encounters
--        (not just index stays) -- a patient's 2nd/3rd stay this
--        year still needs its own risk assessment
WITH prior_admits AS (
    SELECT
        e1.encounter_id,
        COUNT(e2.encounter_id) AS prior_admissions_365d
    FROM encounters AS e1
    LEFT JOIN encounters AS e2
        ON e1.patient_id = e2.patient_id
        AND e2.admission_date < e1.admission_date
        AND e2.admission_date >= DATEADD(DAY, -365, e1.admission_date)
    GROUP BY e1.encounter_id
),

-- STEP 2 (CTE): join patient attributes + prior-admission history
--        onto every encounter, compute a transparent point score
risk_scored AS (
    SELECT
        e.encounter_id,
        e.readmitted_within_30d,
        (
            CASE WHEN p.age >= 75 THEN 2
                 WHEN p.age >= 61 THEN 1
                 ELSE 0 END
          + CASE WHEN e.comorbidity_count >= 3 THEN 2
                 WHEN e.comorbidity_count = 2 THEN 1
                 ELSE 0 END
          + CASE WHEN pa.prior_admissions_365d >= 1 THEN 2 ELSE 0 END
          + CASE WHEN p.insurance_type = 'Self-pay' THEN 1 ELSE 0 END
          + CASE WHEN e.discharge_disposition = 'LAMA' THEN 1 ELSE 0 END
        ) AS risk_points
    FROM encounters AS e
    JOIN patients AS p
        ON e.patient_id = p.patient_id
    JOIN prior_admits AS pa
        ON e.encounter_id = pa.encounter_id
    WHERE e.discharge_disposition <> 'Deceased'    -- can't score/readmit the deceased
)

-- STEP 3: bucket the composite score into tiers, validate against
--        real readmission rate per tier
SELECT
    CASE
        WHEN risk_points <= 1 THEN '1. Low (0-1 pts)'
        WHEN risk_points <= 3 THEN '2. Medium (2-3 pts)'
        ELSE                       '3. High (4+ pts)'
    END                                                     AS risk_tier,
    COUNT(*)                                                AS total_encounters,
    SUM(CAST(readmitted_within_30d AS INT))                 AS readmitted_count,
    CAST(SUM(CAST(readmitted_within_30d AS INT)) AS FLOAT)
        / COUNT(*) * 100                                    AS readmission_rate_pct
FROM risk_scored
GROUP BY
    CASE
        WHEN risk_points <= 1 THEN '1. Low (0-1 pts)'
        WHEN risk_points <= 3 THEN '2. Medium (2-3 pts)'
        ELSE                       '3. High (4+ pts)'
    END
ORDER BY risk_tier;

/* ============================================================
   END OF SCRIPT
   Next step: Python EDA (pandas/matplotlib/seaborn) -- cleaning,
   feature engineering, and the num_medications vs comorbidity_count
   correlation check flagged in Q7, then Power BI dashboard build.
   ============================================================ */
