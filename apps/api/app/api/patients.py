from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_auth_context
from app.db.session import get_db
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.schemas.encounter import EncounterOut
from app.schemas.patient import PatientCreate, PatientOut
from app.services.audit import log_action

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(
    current: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> list[PatientOut]:
    rows = db.execute(
        select(Patient)
        .where(Patient.organization_id == current.organization.id)
        .order_by(Patient.created_at.desc())
    ).scalars().all()
    return [PatientOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("", response_model=PatientOut)
def create_patient(
    payload: PatientCreate,
    current: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> PatientOut:
    patient = Patient(organization_id=current.organization.id, **payload.model_dump())
    db.add(patient)
    db.flush()
    log_action(
        db,
        organization_id=current.organization.id,
        actor_clinician_id=current.clinician.id,
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
    current: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> PatientOut:
    patient = db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.organization_id == current.organization.id,
        )
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientOut.model_validate(patient, from_attributes=True)


@router.get("/{patient_id}/encounters", response_model=list[EncounterOut])
def list_patient_encounters(
    patient_id: int,
    current: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> list[EncounterOut]:
    patient = db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.organization_id == current.organization.id,
        )
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    rows = db.execute(
        select(Encounter)
        .where(
            Encounter.patient_id == patient_id,
            Encounter.organization_id == current.organization.id,
        )
        .order_by(Encounter.created_at.desc())
    ).scalars().all()
    return [EncounterOut.model_validate(r, from_attributes=True) for r in rows]
