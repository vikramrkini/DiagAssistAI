from datetime import datetime

from pydantic import BaseModel


class DashboardKpisOut(BaseModel):
    active_patients: int
    pending_confirmations: int
    high_priority_red_flags_24h: int


class DashboardEncounterItemOut(BaseModel):
    encounter_id: int
    patient_id: int
    patient_name: str
    created_at: datetime
    has_ai_output: bool
    red_flag_count: int
    pending_confirmation: bool
    final_diagnosis_text: str | None


class DashboardTimelineItemOut(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: int
    created_at: datetime
    label: str


class DashboardSummaryOut(BaseModel):
    kpis: DashboardKpisOut
    urgent_queue: list[DashboardEncounterItemOut]
    recent_encounters: list[DashboardEncounterItemOut]
    timeline: list[DashboardTimelineItemOut]
    generated_at: datetime
