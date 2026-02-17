from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.ai import DecisionSupportOutput, StructuredIntake


class EncounterCreate(BaseModel):
    patient_id: int
    transcript_text: str = Field(min_length=1)
    structured_intake_json: StructuredIntake


class EncounterOut(BaseModel):
    id: int
    clinician_id: int
    patient_id: int
    transcript_text: str
    structured_intake_json: StructuredIntake
    final_diagnosis_text: str | None
    created_at: datetime


class ConfirmDiagnosisRequest(BaseModel):
    final_diagnosis_text: str = Field(min_length=2)


class AIOutputOut(BaseModel):
    id: int
    encounter_id: int
    model_version: str
    specialty_used: str
    confidence: float
    uncertainty_notes: str
    created_at: datetime
    output: DecisionSupportOutput
