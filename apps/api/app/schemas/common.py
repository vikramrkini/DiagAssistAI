from datetime import datetime

from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class SafetyDisclaimer(BaseModel):
    banner: str = "Educational demo; not for real clinical use."
    support_notice: str = "Decision support only. Final diagnosis must be clinician-confirmed."


class TimestampedModel(BaseModel):
    id: int
    created_at: datetime
