from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ClinicianOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    specialty: str
    sub_specialty: str | None
    org: str | None
    preferences_json: dict
    created_at: datetime


class ClinicianUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2)
    specialty: str | None = None
    sub_specialty: str | None = None
    org: str | None = None
    preferences_json: dict | None = None
