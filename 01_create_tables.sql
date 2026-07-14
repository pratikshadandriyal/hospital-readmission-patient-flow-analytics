-- Run this in DBeaver's SQL Editor BEFORE importing any CSVs.
-- Creates the schema explicitly so DBeaver's import wizard doesn't
-- have to guess column types (this is what usually breaks CSV imports).

DROP TABLE IF EXISTS encounters;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS doctors;

CREATE TABLE doctors (
    doctor_id           VARCHAR(10) PRIMARY KEY,
    doctor_name         VARCHAR(100),
    department          VARCHAR(50),
    designation         VARCHAR(50),
    years_experience    INT
);

CREATE TABLE patients (
    patient_id          VARCHAR(10) PRIMARY KEY,
    patient_name        VARCHAR(100),
    gender              VARCHAR(5),
    age                 INT,
    city                VARCHAR(50),
    state               VARCHAR(50),
    city_tier           VARCHAR(10),
    insurance_type      VARCHAR(30)
);

CREATE TABLE encounters (
    encounter_id            VARCHAR(10) PRIMARY KEY,
    patient_id              VARCHAR(10) REFERENCES patients(patient_id),
    doctor_id               VARCHAR(10) REFERENCES doctors(doctor_id),
    department              VARCHAR(50),
    diagnosis_category      VARCHAR(30),
    icd10_code              VARCHAR(15),
    icd10_description       VARCHAR(150),
    admission_date          DATE,
    discharge_date          DATE,
    los_days                INT,
    comorbidity_count       INT,
    num_medications         INT,
    num_procedures          INT,
    discharge_disposition   VARCHAR(20),
    total_bill_inr          NUMERIC(12,2),
    oop_amount_inr          NUMERIC(12,2),
    is_readmission          SMALLINT,
    index_encounter_id      VARCHAR(10),   -- nullable, no FK constraint (blank for non-readmissions)
    readmitted_within_30d   SMALLINT
);
