from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_auth_context
from app.db.session import get_db
from app.models.encounter import AIOutput, Encounter
from app.models.guideline import GuidelineChunk, GuidelineDoc
from app.models.patient import Patient
from app.models.audit_log import AuditLog
from app.schemas.encounter import ConfirmDiagnosisRequest, EncounterCreate, EncounterOut
from app.services.audit import log_action

router = APIRouter(prefix="/encounters", tags=["encounters"])


@router.post("", response_model=EncounterOut)
def create_encounter(
    payload: EncounterCreate,
    current: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> EncounterOut:
    patient = db.execute(
        select(Patient).where(
            Patient.id == payload.patient_id,
            Patient.organization_id == current.organization.id,
        )
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    encounter = Encounter(
        organization_id=current.organization.id,
        clinician_id=current.clinician.id,
        patient_id=payload.patient_id,
        transcript_text=payload.transcript_text,
        structured_intake_json=payload.structured_intake_json.model_dump(),
    )
    db.add(encounter)
    db.flush()

    log_action(
        db,
        organization_id=current.organization.id,
        actor_clinician_id=current.clinician.id,
        entity_type="encounter",
        entity_id=encounter.id,
        action="create",
        before_json=None,
        after_json={"patient_id": payload.patient_id},
    )

    db.commit()
    db.refresh(encounter)
    return EncounterOut.model_validate(encounter, from_attributes=True)


@router.get("/{encounter_id}", response_model=EncounterOut)
def get_encounter(
    encounter_id: int,
    current: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> EncounterOut:
    encounter = db.execute(
        select(Encounter).where(
            Encounter.id == encounter_id,
            Encounter.organization_id == current.organization.id,
        )
    ).scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    return EncounterOut.model_validate(encounter, from_attributes=True)


@router.post("/{encounter_id}/confirm-diagnosis", response_model=EncounterOut)
def confirm_diagnosis(
    encounter_id: int,
    payload: ConfirmDiagnosisRequest,
    current: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> EncounterOut:
    encounter = db.execute(
        select(Encounter).where(
            Encounter.id == encounter_id,
            Encounter.organization_id == current.organization.id,
        )
    ).scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    before = {"final_diagnosis_text": encounter.final_diagnosis_text}
    encounter.final_diagnosis_text = payload.final_diagnosis_text
    db.add(encounter)

    log_action(
        db,
        organization_id=current.organization.id,
        actor_clinician_id=current.clinician.id,
        entity_type="encounter",
        entity_id=encounter.id,
        action="confirm_final_diagnosis",
        before_json=before,
        after_json={"final_diagnosis_text": payload.final_diagnosis_text},
    )
    db.commit()
    db.refresh(encounter)
    return EncounterOut.model_validate(encounter, from_attributes=True)


@router.get("/{encounter_id}/evidence")
def get_evidence(
    encounter_id: int,
    current: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    encounter = db.execute(
        select(Encounter).where(
            Encounter.id == encounter_id,
            Encounter.organization_id == current.organization.id,
        )
    ).scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    output = db.execute(
        select(AIOutput).where(AIOutput.encounter_id == encounter_id).order_by(AIOutput.created_at.desc())
    ).scalar_one_or_none()
    if not output:
        return {"encounter_id": encounter_id, "evidence": []}

    chunk_ids = [c.get("chunk_id") for c in output.citations_json if c.get("chunk_id")]
    if not chunk_ids:
        return {"encounter_id": encounter_id, "evidence": []}

    rows = db.execute(
        select(GuidelineChunk, GuidelineDoc)
        .join(GuidelineDoc, GuidelineDoc.id == GuidelineChunk.doc_id)
        .where(GuidelineChunk.id.in_(chunk_ids))
    ).all()

    evidence = [
        {
            "chunk_id": chunk.id,
            "title": doc.title,
            "source": doc.source,
            "specialty_tags": chunk.specialty_tags,
            "chunk_text": chunk.chunk_text,
        }
        for chunk, doc in rows
    ]
    return {"encounter_id": encounter_id, "evidence": evidence}


@router.get("/{encounter_id}/audit")
def get_audit_trail(
    encounter_id: int,
    current: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    encounter = db.execute(
        select(Encounter).where(
            Encounter.id == encounter_id,
            Encounter.organization_id == current.organization.id,
        )
    ).scalar_one_or_none()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    logs = db.execute(
        select(AuditLog)
        .where(
            AuditLog.organization_id == current.organization.id,
            AuditLog.entity_type == "encounter",
            AuditLog.entity_id == encounter_id,
        )
        .order_by(AuditLog.created_at.desc())
    ).scalars().all()
    return {
        "encounter_id": encounter_id,
        "audit_logs": [
            {
                "id": row.id,
                "actor_clinician_id": row.actor_clinician_id,
                "action": row.action,
                "before_json": row.before_json,
                "after_json": row.after_json,
                "created_at": row.created_at.isoformat(),
            }
            for row in logs
        ],
    }
