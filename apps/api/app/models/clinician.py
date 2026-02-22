from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Specialty(StrEnum):
    GENERAL = "general"
    PEDIATRICS = "pediatrics"
    PHYSIOTHERAPY = "physiotherapy"
    DERMATOLOGY = "dermatology"


class Clinician(Base):
    __tablename__ = "clinicians"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[str] = mapped_column(String(50), nullable=False, default=Specialty.GENERAL.value)
    sub_specialty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    org: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferences_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    memberships = relationship("OrganizationMembership", back_populates="clinician", cascade="all, delete-orphan")
    encounters = relationship("Encounter", back_populates="clinician", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="actor", cascade="all, delete-orphan")
