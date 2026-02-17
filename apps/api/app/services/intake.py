import re

from app.schemas.ai import StructuredIntake


SYMPTOM_CANDIDATES = [
    "fever",
    "cough",
    "sore throat",
    "rash",
    "headache",
    "vomiting",
    "diarrhea",
    "pain",
    "fatigue",
    "shortness of breath",
]


NEGATIVE_PATTERNS = [
    r"no chest pain",
    r"no shortness of breath",
    r"no vomiting",
    r"denies (.+?)[\.,]",
]


def extract_structured_intake(transcript: str) -> StructuredIntake:
    lower = transcript.lower()
    symptoms = [s for s in SYMPTOM_CANDIDATES if s in lower]

    negatives: list[str] = []
    for pattern in NEGATIVE_PATTERNS:
        for m in re.finditer(pattern, lower):
            negatives.append(m.group(0))

    chief = transcript.split(".")[0][:180] if transcript else "General clinical concern"
    timeline_match = re.search(r"(\d+\s*(day|days|week|weeks|month|months))", lower)
    timeline = timeline_match.group(1) if timeline_match else "timeline not clearly stated"

    hpi = {
        "context": "derived from transcript",
        "duration": timeline,
        "severity": "not explicitly quantified",
        "modifiers": "limited in transcript",
    }

    return StructuredIntake(
        chief_complaint=chief,
        hpi=hpi,
        relevant_negatives=sorted(set(negatives)),
        timeline=timeline,
        symptoms=symptoms,
    )
