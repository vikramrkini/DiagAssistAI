#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "apps" / "api"))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.clinician import Clinician
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.services.intake import extract_structured_intake

PATIENTS_CSV = ROOT / "data" / "synthea" / "patients.csv"


def seed_clinicians(db: Session) -> list[Clinician]:
    defaults = [
        ("general@demo.local", "General Clinician", "general"),
        ("peds@demo.local", "Pediatrics Clinician", "pediatrics"),
        ("physio@demo.local", "Physiotherapy Clinician", "physiotherapy"),
        ("derm@demo.local", "Dermatology Clinician", "dermatology"),
    ]
    seeded = []
    for email, name, specialty in defaults:
        existing = db.execute(select(Clinician).where(Clinician.email == email)).scalar_one_or_none()
        if existing:
            seeded.append(existing)
            continue
        row = Clinician(
            email=email,
            password_hash=hash_password("demo12345"),
            name=name,
            specialty=specialty,
            org="DiagAssistAI Demo Clinic",
            preferences_json={"tone": "conservative"},
        )
        db.add(row)
        db.flush()
        seeded.append(row)
    return seeded


def seed_patients(db: Session) -> list[Patient]:
    seeded = []
    with open(PATIENTS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for rec in reader:
            existing = db.execute(select(Patient).where(Patient.name == rec["name"])).scalar_one_or_none()
            if existing:
                seeded.append(existing)
                continue
            dob = date.fromisoformat(rec["dob"]) if rec.get("dob") else None
            row = Patient(name=rec["name"], dob=dob, sex=rec["sex"])
            db.add(row)
            db.flush()
            seeded.append(row)
    return seeded


def seed_sample_encounter(db: Session, clinician: Clinician, patient: Patient) -> None:
    transcript = "Patient reports fever for two days, sore throat, and mild cough. No shortness of breath."
    exists = db.execute(
        select(Encounter).where(Encounter.clinician_id == clinician.id, Encounter.patient_id == patient.id)
    ).scalar_one_or_none()
    if exists:
        return
    intake = extract_structured_intake(transcript)
    row = Encounter(
        clinician_id=clinician.id,
        patient_id=patient.id,
        transcript_text=transcript,
        structured_intake_json=intake.model_dump(),
        final_diagnosis_text="Viral upper respiratory illness (clinician-confirmed)",
    )
    db.add(row)


def main() -> None:
    db = SessionLocal()
    try:
        clinicians = seed_clinicians(db)
        patients = seed_patients(db)
        if clinicians and patients:
            seed_sample_encounter(db, clinicians[0], patients[0])
        db.commit()
        print(
            "Seeding complete. logins: general@demo.local / peds@demo.local / physio@demo.local / derm@demo.local (password: demo12345)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
