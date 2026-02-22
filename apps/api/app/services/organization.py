import re
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.clinician import Clinician
from app.models.organization import Organization, OrganizationType
from app.models.organization_membership import OrganizationMembership, OrganizationRole


def slugify_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "organization"


def build_unique_slug(db: Session, base_name: str) -> str:
    base = slugify_name(base_name)
    slug = base
    i = 2
    while db.execute(select(Organization).where(Organization.slug == slug)).scalar_one_or_none():
        slug = f"{base}-{i}"
        i += 1
    return slug


def create_organization(
    db: Session,
    *,
    name: str,
    org_type: OrganizationType,
) -> Organization:
    invite_code = secrets.token_urlsafe(8) if org_type == OrganizationType.HOSPITAL else None
    organization = Organization(
        name=name,
        slug=build_unique_slug(db, name),
        org_type=org_type.value,
        invite_code=invite_code,
    )
    db.add(organization)
    db.flush()
    return organization


def add_membership(
    db: Session,
    *,
    clinician_id: int,
    organization_id: int,
    role: OrganizationRole,
) -> OrganizationMembership:
    membership = OrganizationMembership(
        clinician_id=clinician_id,
        organization_id=organization_id,
        role=role.value,
    )
    db.add(membership)
    db.flush()
    return membership


def ensure_membership_for_clinician(db: Session, clinician: Clinician) -> OrganizationMembership:
    existing = db.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.clinician_id == clinician.id)
        .order_by(OrganizationMembership.created_at.asc())
    ).scalar_one_or_none()
    if existing:
        return existing

    org_name = (clinician.org or "").strip()
    if org_name:
        organization = db.execute(
            select(Organization).where(func.lower(Organization.name) == org_name.casefold())
        ).scalar_one_or_none()
        if not organization:
            organization = create_organization(db, name=org_name, org_type=OrganizationType.HOSPITAL)
        has_members = db.execute(
            select(OrganizationMembership.id).where(OrganizationMembership.organization_id == organization.id).limit(1)
        ).first()
        role = OrganizationRole.OWNER if not has_members else OrganizationRole.CLINICIAN
    else:
        practice_name = f"{clinician.name} Practice"
        organization = create_organization(db, name=practice_name, org_type=OrganizationType.SOLO_PRACTICE)
        clinician.org = organization.name
        db.add(clinician)
        role = OrganizationRole.OWNER

    return add_membership(
        db,
        clinician_id=clinician.id,
        organization_id=organization.id,
        role=role,
    )
