from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_clinician
from app.db.session import get_db
from app.models.clinician import Clinician
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.schemas.encounter import EncounterOut
from app.schemas.patient import PatientCreate, PatientOut
from app.services.audit import log_action

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(
    _: Clinician = Depends(get_current_clinician),
    db: Session = Depends(get_db),
) -> list[PatientOut]:
    rows = db.execute(select(Patient).order_by(Patient.created_at.desc())).scalars().all()
    return [PatientOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("", response_model=PatientOut)
def create_patient(
    payload: PatientCreate,
    current: Clinician = Depends(get_current_clinician),
    db: Session = Depends(get_db),
) -> PatientOut:
    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.flush()
    log_action(
        db,
        actor_clinician_id=current.id,
        entity_type="patient",
        entity_id=patient.id,
        action="create",
        before_json=None,
        after_json=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(patient)
    return PatientOut.model_validate(patient, from_attributes=True)


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int,
    _: Clinician = Depends(get_current_clinician),
    db: Session = Depends(get_db),
) -> PatientOut:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientOut.model_validate(patient, from_attributes=True)


@router.get("/{patient_id}/encounters", response_model=list[EncounterOut])
def list_patient_encounters(
    patient_id: int,
    _: Clinician = Depends(get_current_clinician),
    db: Session = Depends(get_db),
) -> list[EncounterOut]:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    rows = db.execute(
        select(Encounter).where(Encounter.patient_id == patient_id).order_by(Encounter.created_at.desc())
    ).scalars().all()
    return [EncounterOut.model_validate(r, from_attributes=True) for r in rows]
