from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrganizationRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    CLINICIAN = "clinician"
    STAFF = "staff"
    BILLING = "billing"


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("organization_id", "clinician_id", name="uq_organization_membership_org_clinician"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    clinician_id: Mapped[int] = mapped_column(ForeignKey("clinicians.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default=OrganizationRole.CLINICIAN.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="memberships")
    clinician = relationship("Clinician", back_populates="memberships")
