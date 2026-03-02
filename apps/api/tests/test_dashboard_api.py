from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api.dashboard import get_dashboard_summary
from app.api.deps import AuthContext, get_current_auth_context
from app.db.session import get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.clinician import Clinician
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership


class _ScalarRows:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _ResultStub:
    def __init__(
        self,
        *,
        scalar_value: int | None = None,
        rows: list[object] | None = None,
        scalar_rows: list[object] | None = None,
    ) -> None:
        self._scalar_value = scalar_value
        self._rows = rows or []
        self._scalar_rows = scalar_rows or []

    def scalar_one(self) -> int:
        if self._scalar_value is None:
            raise AssertionError("scalar_one() requested without scalar_value")
        return self._scalar_value

    def all(self) -> list[object]:
        return self._rows

    def scalars(self) -> _ScalarRows:
        return _ScalarRows(self._scalar_rows)


class _FakeSession:
    def __init__(self, results: list[_ResultStub]) -> None:
        self._results = list(results)
        self.statements: list[object] = []

    def execute(self, statement: object) -> _ResultStub:
        if not self._results:
            raise AssertionError("No stubbed result available for execute()")
        self.statements.append(statement)
        return self._results.pop(0)


def _compile_sql(statement: object) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def _auth_context(org_id: int = 77) -> AuthContext:
    clinician = Clinician(
        id=900,
        email="dash-test@example.com",
        password_hash="hashed",
        name="Dash Test",
        specialty="general",
        preferences_json={},
    )
    organization = Organization(
        id=org_id,
        name=f"Org {org_id}",
        slug=f"org-{org_id}",
        org_type="hospital",
        invite_code=None,
    )
    membership = OrganizationMembership(
        id=800,
        organization_id=org_id,
        clinician_id=clinician.id,
        role="clinician",
    )
    return AuthContext(clinician=clinician, organization=organization, membership=membership)


def _base_result_stubs() -> list[_ResultStub]:
    return [
        _ResultStub(scalar_value=0),
        _ResultStub(scalar_value=0),
        _ResultStub(scalar_value=0),
        _ResultStub(rows=[]),
        _ResultStub(rows=[]),
        _ResultStub(scalar_rows=[]),
    ]


def test_dashboard_summary_queries_are_organization_scoped() -> None:
    db = _FakeSession(_base_result_stubs())
    summary = get_dashboard_summary(recent_limit=8, timeline_limit=12, current=_auth_context(org_id=77), db=db)  # type: ignore[arg-type]

    assert summary.kpis.active_patients == 0
    assert summary.urgent_queue == []
    assert len(db.statements) == 6

    patients_sql = _compile_sql(db.statements[0]).lower()
    pending_sql = _compile_sql(db.statements[1]).lower()
    red_flags_sql = _compile_sql(db.statements[2]).lower()
    urgent_sql = _compile_sql(db.statements[3]).lower()
    recent_sql = _compile_sql(db.statements[4]).lower()
    timeline_sql = _compile_sql(db.statements[5]).lower()

    assert "patients.organization_id = 77" in patients_sql
    assert "encounters.organization_id = 77" in pending_sql
    assert "encounters.organization_id = 77" in red_flags_sql
    assert "encounters.organization_id = 77" in urgent_sql
    assert "patients.organization_id = 77" in urgent_sql
    assert "encounters.organization_id = 77" in recent_sql
    assert "audit_logs.organization_id = 77" in timeline_sql


def test_pending_confirmation_logic_handles_null_and_blank() -> None:
    now = datetime.now(UTC)
    urgent_rows = [
        SimpleNamespace(
            encounter_id=10,
            patient_id=101,
            patient_name="Alex One",
            created_at=now,
            final_diagnosis_text=None,
            ai_output_id=1,
            red_flag_count=2,
        ),
        SimpleNamespace(
            encounter_id=11,
            patient_id=102,
            patient_name="Alex Two",
            created_at=now,
            final_diagnosis_text="   ",
            ai_output_id=None,
            red_flag_count=0,
        ),
    ]
    recent_rows = urgent_rows + [
        SimpleNamespace(
            encounter_id=12,
            patient_id=103,
            patient_name="Alex Three",
            created_at=now,
            final_diagnosis_text="Likely influenza",
            ai_output_id=2,
            red_flag_count=1,
        )
    ]
    db = _FakeSession(
        [
            _ResultStub(scalar_value=3),
            _ResultStub(scalar_value=2),
            _ResultStub(scalar_value=1),
            _ResultStub(rows=urgent_rows),
            _ResultStub(rows=recent_rows),
            _ResultStub(scalar_rows=[]),
        ]
    )

    summary = get_dashboard_summary(recent_limit=8, timeline_limit=12, current=_auth_context(), db=db)  # type: ignore[arg-type]

    pending_sql = _compile_sql(db.statements[1]).lower()
    assert "final_diagnosis_text is null" in pending_sql
    assert "trim(encounters.final_diagnosis_text)" in pending_sql

    assert summary.kpis.pending_confirmations == 2
    assert all(item.pending_confirmation for item in summary.urgent_queue)
    assert summary.recent_encounters[2].pending_confirmation is False
    assert summary.recent_encounters[2].final_diagnosis_text == "Likely influenza"


def test_high_priority_red_flags_24h_uses_latest_ai_output_and_flags() -> None:
    db = _FakeSession(_base_result_stubs())
    summary = get_dashboard_summary(recent_limit=8, timeline_limit=12, current=_auth_context(), db=db)  # type: ignore[arg-type]
    red_flags_sql = _compile_sql(db.statements[2]).lower()

    assert summary.kpis.high_priority_red_flags_24h == 0
    assert "row_number() over (partition by ai_outputs.encounter_id" in red_flags_sql
    assert "jsonb_array_length(ai_outputs.red_flags_json)" in red_flags_sql
    assert "latest_ai.ai_created_at >=" in red_flags_sql
    assert "latest_ai.red_flag_count > 0" in red_flags_sql


def test_timeline_filters_allowed_actions_and_labels_are_derived() -> None:
    now = datetime.now(UTC)
    timeline_rows = [
        AuditLog(
            id=1,
            organization_id=77,
            actor_clinician_id=900,
            entity_type="encounter",
            entity_id=101,
            action="create",
            before_json=None,
            after_json=None,
            created_at=now,
        ),
        AuditLog(
            id=2,
            organization_id=77,
            actor_clinician_id=900,
            entity_type="ai_output",
            entity_id=201,
            action="generate_decision_support",
            before_json=None,
            after_json=None,
            created_at=now,
        ),
        AuditLog(
            id=3,
            organization_id=77,
            actor_clinician_id=900,
            entity_type="encounter",
            entity_id=101,
            action="confirm_final_diagnosis",
            before_json=None,
            after_json=None,
            created_at=now,
        ),
    ]
    db = _FakeSession(
        [
            _ResultStub(scalar_value=0),
            _ResultStub(scalar_value=0),
            _ResultStub(scalar_value=0),
            _ResultStub(rows=[]),
            _ResultStub(rows=[]),
            _ResultStub(scalar_rows=timeline_rows),
        ]
    )

    summary = get_dashboard_summary(recent_limit=8, timeline_limit=12, current=_auth_context(), db=db)  # type: ignore[arg-type]
    timeline_sql = _compile_sql(db.statements[5]).lower()

    assert "audit_logs.entity_type = 'encounter' and audit_logs.action = 'create'" in timeline_sql
    assert "audit_logs.entity_type = 'encounter' and audit_logs.action = 'confirm_final_diagnosis'" in timeline_sql
    assert "audit_logs.entity_type = 'ai_output' and audit_logs.action = 'generate_decision_support'" in timeline_sql
    assert "order by audit_logs.created_at desc, audit_logs.id desc" in timeline_sql
    assert [item.label for item in summary.timeline] == [
        "Encounter created",
        "Decision support generated",
        "Final diagnosis confirmed",
    ]


def test_dashboard_limits_are_enforced() -> None:
    client = TestClient(app)
    app.dependency_overrides[get_current_auth_context] = lambda: _auth_context()
    app.dependency_overrides[get_db] = lambda: _FakeSession(_base_result_stubs())
    try:
        too_high_recent = client.get("/dashboard/summary", params={"recent_limit": 999})
        too_high_timeline = client.get("/dashboard/summary", params={"timeline_limit": 999})
    finally:
        app.dependency_overrides.clear()

    assert too_high_recent.status_code == 422
    assert too_high_timeline.status_code == 422

    db = _FakeSession(_base_result_stubs())
    get_dashboard_summary(recent_limit=3, timeline_limit=5, current=_auth_context(), db=db)  # type: ignore[arg-type]
    urgent_sql = _compile_sql(db.statements[3]).lower()
    recent_sql = _compile_sql(db.statements[4]).lower()
    timeline_sql = _compile_sql(db.statements[5]).lower()
    assert "limit 3" in urgent_sql
    assert "limit 3" in recent_sql
    assert "limit 5" in timeline_sql


def test_empty_organization_returns_zeroed_dashboard() -> None:
    db = _FakeSession(_base_result_stubs())
    summary = get_dashboard_summary(recent_limit=8, timeline_limit=12, current=_auth_context(), db=db)  # type: ignore[arg-type]

    assert summary.kpis.active_patients == 0
    assert summary.kpis.pending_confirmations == 0
    assert summary.kpis.high_priority_red_flags_24h == 0
    assert summary.urgent_queue == []
    assert summary.recent_encounters == []
    assert summary.timeline == []
