from pydantic import ValidationError

from app.schemas.ai import DecisionSupportOutput


def test_decision_support_schema_accepts_valid_payload() -> None:
    payload = {
        "differential": [{"name": "Viral syndrome", "likelihood_bucket": "moderate", "rationale": "symptoms", "citations": [1]}],
        "red_flags": [{"flag": "respiratory distress", "why": "risk", "action": "urgent evaluation", "citations": [1]}],
        "followups": [{"question": "Any dyspnea?", "why": "triage", "citations": [1]}],
        "tests": [{"test": "Pulse oximetry", "why": "screening", "citations": [1]}],
        "confidence": 0.5,
        "uncertainty_notes": "Needs clinician review",
        "needs_human_review": True,
        "citations": [{"chunk_id": 1, "source": "repo://guideline", "title": "T", "excerpt": "E"}],
    }
    output = DecisionSupportOutput.model_validate(payload)
    assert output.needs_human_review is True
    assert output.differential[0].citations == [1]


def test_decision_support_confidence_bounds() -> None:
    payload = {
        "differential": [],
        "red_flags": [],
        "followups": [],
        "tests": [],
        "confidence": 2.0,
        "uncertainty_notes": "x",
        "needs_human_review": True,
        "citations": [],
    }
    try:
        DecisionSupportOutput.model_validate(payload)
        assert False, "Expected validation error"
    except ValidationError:
        assert True
