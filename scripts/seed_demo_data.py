#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Resolve API package path for both local repo layout and Docker compose mounts.
api_path_candidates = (ROOT / "apps" / "api", Path("/app"))
for api_path in api_path_candidates:
    if (api_path / "app").exists():
        # Prepend so the project package wins over any third-party `app` package.
        sys.path.insert(0, str(api_path))
        break
else:
    raise RuntimeError("Could not locate API package path for seed script.")

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.clinician import Clinician
from app.models.encounter import Encounter
from app.models.organization import Organization, OrganizationType
from app.models.organization_membership import OrganizationMembership, OrganizationRole
from app.models.patient import Patient
from app.services.organization import add_membership, create_organization
from app.services.intake import extract_structured_intake

PATIENTS_CSV = ROOT / "data" / "synthea" / "patients.csv"


def ensure_demo_organization(db: Session) -> Organization:
    org = db.execute(
        select(Organization).where(Organization.name == "DiagAssistAI Demo Clinic")
    ).scalar_one_or_none()
    if org:
        return org
    return create_organization(db, name="DiagAssistAI Demo Clinic", org_type=OrganizationType.HOSPITAL)


def seed_clinicians(db: Session, organization: Organization) -> list[Clinician]:
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
            membership = db.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.clinician_id == existing.id,
                    OrganizationMembership.organization_id == organization.id,
                )
            ).scalar_one_or_none()
            if not membership:
                role = OrganizationRole.OWNER if email == "general@demo.local" else OrganizationRole.CLINICIAN
                add_membership(
                    db,
                    clinician_id=existing.id,
                    organization_id=organization.id,
                    role=role,
                )
            if existing.org != organization.name:
                existing.org = organization.name
                db.add(existing)
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
        role = OrganizationRole.OWNER if email == "general@demo.local" else OrganizationRole.CLINICIAN
        add_membership(
            db,
            clinician_id=row.id,
            organization_id=organization.id,
            role=role,
        )
        seeded.append(row)
    return seeded


def seed_patients(db: Session, organization: Organization) -> list[Patient]:
    seeded = []
    with open(PATIENTS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for rec in reader:
            existing = db.execute(
                select(Patient).where(
                    Patient.organization_id == organization.id,
                    Patient.name == rec["name"],
                )
            ).scalar_one_or_none()
            if existing:
                seeded.append(existing)
                continue
            dob = date.fromisoformat(rec["dob"]) if rec.get("dob") else None
            row = Patient(
                organization_id=organization.id,
                name=rec["name"],
                dob=dob,
                sex=rec["sex"],
            )
            db.add(row)
            db.flush()
            seeded.append(row)
    return seeded


def seed_sample_encounter(db: Session, organization: Organization, clinician: Clinician, patient: Patient) -> None:
    transcript = "Patient reports fever for two days, sore throat, and mild cough. No shortness of breath."
    exists = db.execute(
        select(Encounter).where(
            Encounter.organization_id == organization.id,
            Encounter.clinician_id == clinician.id,
            Encounter.patient_id == patient.id,
        )
    ).scalar_one_or_none()
    if exists:
        return
    intake = extract_structured_intake(transcript)
    row = Encounter(
        organization_id=organization.id,
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
        organization = ensure_demo_organization(db)
        clinicians = seed_clinicians(db, organization)
        patients = seed_patients(db, organization)
        if clinicians and patients:
            seed_sample_encounter(db, organization, clinicians[0], patients[0])
        db.commit()
        print(
            "Seeding complete. logins: general@demo.local / peds@demo.local / physio@demo.local / derm@demo.local (password: demo12345)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
