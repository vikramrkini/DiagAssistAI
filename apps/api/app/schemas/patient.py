from datetime import date, datetime

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    name: str = Field(min_length=2)
    dob: date | None = None
    sex: str | None = None


class PatientOut(BaseModel):
    id: int
    organization_id: int
    name: str
    dob: date | None
    sex: str | None
    created_at: datetime
