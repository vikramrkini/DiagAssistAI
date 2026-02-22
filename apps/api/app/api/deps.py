from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.clinician import Clinician
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.services.organization import ensure_membership_for_clinician

bearer = HTTPBearer(auto_error=False)


def get_token_from_request(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str | None:
    if creds:
        return creds.credentials
    cookie_token = request.cookies.get("diagassist_token")
    return cookie_token


def get_current_clinician(
    db: Session = Depends(get_db),
    token: str | None = Depends(get_token_from_request),
) -> Clinician:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

    clinician_id = payload.get("clinician_id")
    clinician = db.get(Clinician, clinician_id)
    if not clinician:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clinician not found")
    return clinician


@dataclass
class AuthContext:
    clinician: Clinician
    organization: Organization
    membership: OrganizationMembership


def get_current_auth_context(
    db: Session = Depends(get_db),
    token: str | None = Depends(get_token_from_request),
) -> AuthContext:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

    clinician_id = payload.get("clinician_id")
    clinician = db.get(Clinician, clinician_id)
    if not clinician:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clinician not found")

    token_org_id = payload.get("organization_id")
    if token_org_id is not None:
        try:
            token_org_id = int(token_org_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid organization in auth token") from exc
    membership_query = select(OrganizationMembership).where(OrganizationMembership.clinician_id == clinician.id)
    if token_org_id:
        membership_query = membership_query.where(OrganizationMembership.organization_id == token_org_id)
    membership = db.execute(membership_query.order_by(OrganizationMembership.created_at.asc())).scalar_one_or_none()
    if not membership:
        fallback = db.execute(
            select(OrganizationMembership)
            .where(OrganizationMembership.clinician_id == clinician.id)
            .order_by(OrganizationMembership.created_at.asc())
        ).scalar_one_or_none()
        if not fallback:
            fallback = ensure_membership_for_clinician(db, clinician)
            db.commit()
            db.refresh(fallback)
        membership = fallback

    organization = db.get(Organization, membership.organization_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization not found")

    return AuthContext(clinician=clinician, organization=organization, membership=membership)
