import json
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.schemas.ai import Citation, DecisionSupportOutput
from app.services.specialty import specialty_store


def _limit_items(items: list[dict], max_items: int) -> list[dict]:
    return items[:max_items]


def _enforce_citations(payload: dict[str, Any]) -> dict[str, Any]:
    fields = ["differential", "red_flags", "followups", "tests"]
    for field in fields:
        normalized = []
        for item in payload.get(field, []):
            citations = item.get("citations", [])
            if not citations:
                item["no_evidence"] = True
                if "likelihood_bucket" in item:
                    item["likelihood_bucket"] = "low"
            normalized.append(item)
        payload[field] = normalized
    return payload


def _demo_output(transcript: str, specialty: str, citation_ids: list[int], citations: list[Citation]) -> dict[str, Any]:
    template = specialty_store.get(specialty)
    diff_names = template["differential_starters"]
    followups = template["followup_starters"]
    tests = template["test_starters"]

    def citation_or_empty(idx: int) -> list[int]:
        return [citation_ids[idx]] if idx < len(citation_ids) else []

    output = {
        "differential": [
            {
                "name": diff_names[0],
                "likelihood_bucket": "moderate",
                "rationale": f"Based on transcript findings: {transcript[:120]}",
                "citations": citation_or_empty(0),
            },
            {
                "name": diff_names[1],
                "likelihood_bucket": "low-moderate",
                "rationale": "Needs targeted follow-up to rule in/out.",
                "citations": citation_or_empty(1),
            },
        ],
        "red_flags": [
            {
                "flag": template["red_flag_focus"],
                "why": "Potential acute deterioration risk if present.",
                "action": "Escalate to urgent in-person assessment when positive.",
                "citations": citation_or_empty(0),
            }
        ],
        "followups": [{"question": q, "why": "Reduce uncertainty.", "citations": citation_or_empty(i)} for i, q in enumerate(followups)],
        "tests": [{"test": t, "why": "Clarify likely causes.", "citations": citation_or_empty(i)} for i, t in enumerate(tests)],
        "confidence": 0.43,
        "uncertainty_notes": "Needs human review; transcript context is limited.",
        "needs_human_review": True,
        "citations": [c.model_dump() for c in citations],
    }
    output["followups"] = _limit_items(output["followups"], template["max_followups"])
    output["tests"] = _limit_items(output["tests"], template["max_tests"])
    return _enforce_citations(output)


def _openai_output(prompt: str, specialty: str, citations: list[Citation]) -> dict[str, Any]:
    client = OpenAI(api_key=settings.openai_api_key)
    template = specialty_store.get(specialty)
    schema_hint = {
        "differential": [{"name": "", "likelihood_bucket": "", "rationale": "", "citations": [0]}],
        "red_flags": [{"flag": "", "why": "", "action": "", "citations": [0]}],
        "followups": [{"question": "", "why": "", "citations": [0]}],
        "tests": [{"test": "", "why": "", "citations": [0]}],
        "confidence": 0.0,
        "uncertainty_notes": "",
    }
    msg = (
        "You are a clinical decision-support assistant. Never provide definitive diagnosis. "
        f"Specialty context: {specialty}. Template constraints: {json.dumps(template)}. "
        "Output strict JSON matching schema, cite chunk IDs only."
        f"Schema example: {json.dumps(schema_hint)}. Prompt: {prompt}"
    )
    resp = client.responses.create(model="gpt-4.1-mini", input=msg)
    text = resp.output_text
    parsed = json.loads(text)
    parsed["needs_human_review"] = True
    parsed["citations"] = [c.model_dump() for c in citations]
    return _enforce_citations(parsed)


def generate_decision_support(
    transcript: str,
    specialty: str,
    retrieved_chunks: list[dict],
) -> DecisionSupportOutput:
    citations = [
        Citation(
            chunk_id=c["chunk_id"],
            source=c["source"],
            title=c["title"],
            excerpt=c["excerpt"],
        )
        for c in retrieved_chunks
    ]
    citation_ids = [c.chunk_id for c in citations]

    prompt = {
        "transcript": transcript,
        "specialty": specialty,
        "evidence": [c.model_dump() for c in citations],
    }

    if settings.openai_api_key:
        try:
            payload = _openai_output(json.dumps(prompt), specialty, citations)
        except Exception:
            payload = _demo_output(transcript, specialty, citation_ids, citations)
    else:
        payload = _demo_output(transcript, specialty, citation_ids, citations)

    return DecisionSupportOutput.model_validate(payload)
