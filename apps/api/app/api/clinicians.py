from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_auth_context
from app.db.session import get_db
from app.models.clinician import Clinician
from app.models.organization_membership import OrganizationMembership, OrganizationRole
from app.schemas.clinician import ClinicianOut, ClinicianUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/clinicians", tags=["clinicians"])


@router.get("/me", response_model=ClinicianOut)
def get_me(current: AuthContext = Depends(get_current_auth_context)) -> ClinicianOut:
    current.clinician.org = current.organization.name
    return ClinicianOut.model_validate(current.clinician, from_attributes=True)


@router.put("/me", response_model=ClinicianOut)
def update_me(
    payload: ClinicianUpdate,
    db: Session = Depends(get_db),
    current: AuthContext = Depends(get_current_auth_context),
) -> ClinicianOut:
    clinician = current.clinician
    before = {
        "name": clinician.name,
        "specialty": clinician.specialty,
        "sub_specialty": clinician.sub_specialty,
        "org": current.organization.name,
        "preferences_json": clinician.preferences_json,
    }

    updates = payload.model_dump(exclude_none=True)
    requested_org_name = updates.pop("org", None)
    for key, value in updates.items():
        setattr(clinician, key, value)

    if requested_org_name:
        if current.membership.role not in {OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners/admins can update organization name",
            )
        current.organization.name = requested_org_name
        db.add(current.organization)
        members = db.execute(
            select(Clinician)
            .join(OrganizationMembership, OrganizationMembership.clinician_id == Clinician.id)
            .where(OrganizationMembership.organization_id == current.organization.id)
        ).scalars().all()
        for member in members:
            member.org = requested_org_name
            db.add(member)
        updates["org"] = requested_org_name

    db.add(clinician)
    log_action(
        db,
        organization_id=current.organization.id,
        actor_clinician_id=clinician.id,
        entity_type="clinician",
        entity_id=clinician.id,
        action="update_profile",
        before_json=before,
        after_json=updates,
    )
    db.commit()
    db.refresh(clinician)
    clinician.org = current.organization.name
    return ClinicianOut.model_validate(clinician, from_attributes=True)
