from app.services.decision_support import generate_decision_support
from app.services.intake import extract_structured_intake


def test_extract_structured_intake_has_expected_shape() -> None:
    transcript = "Fever for 3 days with cough. No shortness of breath."
    intake = extract_structured_intake(transcript)
    assert intake.chief_complaint
    assert "duration" in intake.hpi
    assert isinstance(intake.symptoms, list)


def test_decision_support_requires_human_review() -> None:
    out = generate_decision_support(
        transcript="Rash with itch, no fever.",
        specialty="dermatology",
        retrieved_chunks=[
            {
                "chunk_id": 10,
                "source": "repo://data/guidelines/dermatology_rash.md",
                "title": "Derm",
                "excerpt": "red flags include mucosal involvement",
            }
        ],
    )
    assert out.needs_human_review is True
    assert len(out.citations) >= 1
    assert all(item.citations or item.no_evidence for item in out.differential)
