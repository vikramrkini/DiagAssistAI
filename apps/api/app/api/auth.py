from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_auth_context
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.clinician import Clinician
from app.models.organization import Organization, OrganizationType
from app.models.organization_membership import OrganizationMembership, OrganizationRole
from app.schemas.auth import AuthTokenResponse, LoginRequest, MeResponse, SignUpRequest
from app.services.organization import add_membership, create_organization, ensure_membership_for_clinician
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthTokenResponse)
def signup(payload: SignUpRequest, response: Response, db: Session = Depends(get_db)) -> AuthTokenResponse:
    existing = db.execute(select(Clinician).where(Clinician.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    if payload.hospital_invite_code:
        organization = db.execute(
            select(Organization).where(
                Organization.invite_code == payload.hospital_invite_code,
                Organization.org_type == OrganizationType.HOSPITAL.value,
            )
        ).scalar_one_or_none()
        if not organization:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid hospital invite code")
        membership_role = OrganizationRole.CLINICIAN
    else:
        if payload.account_type == "hospital":
            org_name = payload.organization_name or "New Hospital Organization"
            organization = create_organization(db, name=org_name, org_type=OrganizationType.HOSPITAL)
            membership_role = OrganizationRole.OWNER
        else:
            org_name = payload.organization_name or f"{payload.name} Practice"
            organization = create_organization(db, name=org_name, org_type=OrganizationType.SOLO_PRACTICE)
            membership_role = OrganizationRole.OWNER

    clinician = Clinician(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        specialty=payload.specialty,
        org=organization.name,
    )
    db.add(clinician)
    db.flush()
    membership = add_membership(
        db,
        clinician_id=clinician.id,
        organization_id=organization.id,
        role=membership_role,
    )

    log_action(
        db,
        organization_id=organization.id,
        actor_clinician_id=clinician.id,
        entity_type="clinician",
        entity_id=clinician.id,
        action="signup",
        before_json=None,
        after_json={
            "email": clinician.email,
            "specialty": clinician.specialty,
            "organization_id": organization.id,
            "organization_type": organization.org_type,
            "role": membership.role,
        },
    )

    token = create_access_token(payload.email, clinician.id, organization.id)
    db.commit()
    response.set_cookie("diagassist_token", token, httponly=True, samesite="lax")
    return AuthTokenResponse(access_token=token)


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthTokenResponse:
    clinician = db.execute(select(Clinician).where(Clinician.email == payload.email)).scalar_one_or_none()
    if not clinician or not verify_password(payload.password, clinician.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    membership = db.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.clinician_id == clinician.id)
        .order_by(OrganizationMembership.created_at.asc())
    ).scalar_one_or_none()
    if not membership:
        membership = ensure_membership_for_clinician(db, clinician)
        db.commit()
        db.refresh(membership)

    token = create_access_token(clinician.email, clinician.id, membership.organization_id)
    response.set_cookie("diagassist_token", token, httponly=True, samesite="lax")
    return AuthTokenResponse(access_token=token)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie("diagassist_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=MeResponse)
def me(current: AuthContext = Depends(get_current_auth_context)) -> MeResponse:
    show_invite_code = current.membership.role in {OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value}
    return MeResponse(
        id=current.clinician.id,
        email=current.clinician.email,
        name=current.clinician.name,
        specialty=current.clinician.specialty,
        organization_id=current.organization.id,
        organization_name=current.organization.name,
        organization_type=current.organization.org_type,
        role=current.membership.role,
        hospital_invite_code=current.organization.invite_code if show_invite_code else None,
    )
