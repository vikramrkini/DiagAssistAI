import json
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.schemas.ai import Citation, DecisionSupportOutput
from app.services.specialty import specialty_store


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


def _openai_output(prompt: str, specialty: str, citations: list[Citation]) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for decision support generation.")

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
    prompt = {
        "transcript": transcript,
        "specialty": specialty,
        "evidence": [c.model_dump() for c in citations],
    }

    payload = _openai_output(json.dumps(prompt), specialty, citations)
    return DecisionSupportOutput.model_validate(payload)
