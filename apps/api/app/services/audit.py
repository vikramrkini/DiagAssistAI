from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    actor_clinician_id: int | None,
    entity_type: str,
    entity_id: int,
    action: str,
    before_json: dict | None,
    after_json: dict | None,
) -> None:
    event = AuditLog(
        actor_clinician_id=actor_clinician_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=before_json,
        after_json=after_json,
    )
    db.add(event)
