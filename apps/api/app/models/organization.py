from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrganizationType(StrEnum):
    SOLO_PRACTICE = "solo_practice"
    HOSPITAL = "hospital"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    org_type: Mapped[str] = mapped_column(String(40), nullable=False)
    invite_code: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    memberships = relationship("OrganizationMembership", back_populates="organization", cascade="all, delete-orphan")
    patients = relationship("Patient", back_populates="organization")
    encounters = relationship("Encounter", back_populates="organization")
    audit_logs = relationship("AuditLog", back_populates="organization")
