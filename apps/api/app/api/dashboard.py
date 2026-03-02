from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_auth_context
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.encounter import AIOutput, Encounter
from app.models.patient import Patient
from app.schemas.dashboard import (
    DashboardEncounterItemOut,
    DashboardKpisOut,
    DashboardSummaryOut,
    DashboardTimelineItemOut,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _is_pending_confirmation_expr() -> object:
    return or_(
        Encounter.final_diagnosis_text.is_(None),
        func.length(func.trim(Encounter.final_diagnosis_text)) == 0,
    )


def _timeline_label(action: str) -> str:
    if action == "create":
        return "Encounter created"
    if action == "generate_decision_support":
        return "Decision support generated"
    if action == "confirm_final_diagnosis":
        return "Final diagnosis confirmed"
    return action.replace("_", " ").capitalize()


@router.get("/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(
    recent_limit: int = Query(default=8, ge=1, le=20),
    timeline_limit: int = Query(default=12, ge=1, le=30),
    current: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> DashboardSummaryOut:
    org_id = current.organization.id
    now_utc = datetime.now(timezone.utc)
    red_flag_cutoff = now_utc - timedelta(hours=24)

    latest_ai_ranked = (
        select(
            AIOutput.id.label("ai_output_id"),
            AIOutput.encounter_id.label("encounter_id"),
            AIOutput.created_at.label("ai_created_at"),
            func.coalesce(func.jsonb_array_length(AIOutput.red_flags_json), 0).label("red_flag_count"),
            func.row_number()
            .over(partition_by=AIOutput.encounter_id, order_by=(AIOutput.created_at.desc(), AIOutput.id.desc()))
            .label("rn"),
        )
        .subquery("latest_ai_ranked")
    )
    latest_ai = (
        select(
            latest_ai_ranked.c.ai_output_id,
            latest_ai_ranked.c.encounter_id,
            latest_ai_ranked.c.ai_created_at,
            latest_ai_ranked.c.red_flag_count,
        )
        .where(latest_ai_ranked.c.rn == 1)
        .subquery("latest_ai")
    )

    active_patients = db.execute(
        select(func.count())
        .select_from(Patient)
        .where(Patient.organization_id == org_id)
    ).scalar_one()

    pending_confirmations = db.execute(
        select(func.count())
        .select_from(Encounter)
        .where(Encounter.organization_id == org_id, _is_pending_confirmation_expr())
    ).scalar_one()

    high_priority_red_flags_24h = db.execute(
        select(func.count())
        .select_from(Encounter)
        .join(latest_ai, latest_ai.c.encounter_id == Encounter.id)
        .where(
            Encounter.organization_id == org_id,
            latest_ai.c.ai_created_at >= red_flag_cutoff,
            latest_ai.c.red_flag_count > 0,
        )
    ).scalar_one()

    def fetch_encounters(limit_value: int, pending_only: bool) -> list[DashboardEncounterItemOut]:
        stmt = (
            select(
                Encounter.id.label("encounter_id"),
                Encounter.patient_id.label("patient_id"),
                Patient.name.label("patient_name"),
                Encounter.created_at.label("created_at"),
                Encounter.final_diagnosis_text.label("final_diagnosis_text"),
                latest_ai.c.ai_output_id.label("ai_output_id"),
                func.coalesce(latest_ai.c.red_flag_count, 0).label("red_flag_count"),
            )
            .join(Patient, Patient.id == Encounter.patient_id)
            .outerjoin(latest_ai, latest_ai.c.encounter_id == Encounter.id)
            .where(
                Encounter.organization_id == org_id,
                Patient.organization_id == org_id,
            )
            .order_by(Encounter.created_at.desc())
            .limit(limit_value)
        )
        if pending_only:
            stmt = stmt.where(_is_pending_confirmation_expr())

        rows = db.execute(stmt).all()
        items: list[DashboardEncounterItemOut] = []
        for row in rows:
            final_diagnosis = row.final_diagnosis_text
            pending_confirmation = final_diagnosis is None or not final_diagnosis.strip()
            items.append(
                DashboardEncounterItemOut(
                    encounter_id=row.encounter_id,
                    patient_id=row.patient_id,
                    patient_name=row.patient_name,
                    created_at=row.created_at,
                    has_ai_output=row.ai_output_id is not None,
                    red_flag_count=int(row.red_flag_count or 0),
                    pending_confirmation=pending_confirmation,
                    final_diagnosis_text=final_diagnosis,
                )
            )
        return items

    urgent_queue = fetch_encounters(limit_value=recent_limit, pending_only=True)
    recent_encounters = fetch_encounters(limit_value=recent_limit, pending_only=False)

    timeline_rows = db.execute(
        select(AuditLog)
        .where(
            AuditLog.organization_id == org_id,
            or_(
                and_(AuditLog.entity_type == "encounter", AuditLog.action == "create"),
                and_(AuditLog.entity_type == "encounter", AuditLog.action == "confirm_final_diagnosis"),
                and_(AuditLog.entity_type == "ai_output", AuditLog.action == "generate_decision_support"),
            ),
        )
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(timeline_limit)
    ).scalars().all()

    timeline = [
        DashboardTimelineItemOut(
            id=row.id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            created_at=row.created_at,
            label=_timeline_label(row.action),
        )
        for row in timeline_rows
    ]

    return DashboardSummaryOut(
        kpis=DashboardKpisOut(
            active_patients=int(active_patients),
            pending_confirmations=int(pending_confirmations),
            high_priority_red_flags_24h=int(high_priority_red_flags_24h),
        ),
        urgent_queue=urgent_queue,
        recent_encounters=recent_encounters,
        timeline=timeline,
        generated_at=now_utc,
    )
