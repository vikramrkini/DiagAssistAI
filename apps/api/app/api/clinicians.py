from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_clinician
from app.db.session import get_db
from app.models.clinician import Clinician
from app.schemas.clinician import ClinicianOut, ClinicianUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/clinicians", tags=["clinicians"])


@router.get("/me", response_model=ClinicianOut)
def get_me(current: Clinician = Depends(get_current_clinician)) -> ClinicianOut:
    return ClinicianOut.model_validate(current, from_attributes=True)


@router.put("/me", response_model=ClinicianOut)
def update_me(
    payload: ClinicianUpdate,
    db: Session = Depends(get_db),
    current: Clinician = Depends(get_current_clinician),
) -> ClinicianOut:
    before = {
        "name": current.name,
        "specialty": current.specialty,
        "sub_specialty": current.sub_specialty,
        "org": current.org,
        "preferences_json": current.preferences_json,
    }

    updates = payload.model_dump(exclude_none=True)
    for key, value in updates.items():
        setattr(current, key, value)

    db.add(current)
    log_action(
        db,
        actor_clinician_id=current.id,
        entity_type="clinician",
        entity_id=current.id,
        action="update_profile",
        before_json=before,
        after_json=updates,
    )
    db.commit()
    db.refresh(current)
    return ClinicianOut.model_validate(current, from_attributes=True)
