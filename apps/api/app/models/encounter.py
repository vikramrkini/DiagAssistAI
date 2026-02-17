from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Encounter(Base):
    __tablename__ = "encounters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    clinician_id: Mapped[int] = mapped_column(ForeignKey("clinicians.id", ondelete="CASCADE"), index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured_intake_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    final_diagnosis_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    clinician = relationship("Clinician", back_populates="encounters")
    patient = relationship("Patient", back_populates="encounters")
    ai_outputs = relationship("AIOutput", back_populates="encounter", cascade="all, delete-orphan")


class AIOutput(Base):
    __tablename__ = "ai_outputs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    encounter_id: Mapped[int] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"), index=True, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    specialty_used: Mapped[str] = mapped_column(Text, nullable=False)
    differential_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    red_flags_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    followups_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tests_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    citations_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    uncertainty_notes: Mapped[str] = mapped_column(Text, nullable=False, default="Needs clinician review.")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    encounter = relationship("Encounter", back_populates="ai_outputs")
