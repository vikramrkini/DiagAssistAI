from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_auth_context
from app.db.session import get_db
from app.models.encounter import AIOutput, Encounter
from app.schemas.ai import DecisionSupportRequest, DecisionSupportOutput, ExtractIntakeRequest, StructuredIntake, TranscribeResponse
from app.services.audit import log_action
from app.services.decision_support import generate_decision_support
from app.services.intake import extract_structured_intake
from app.services.retrieval import retrieve_chunks
from app.services.transcription import transcribe

router = APIRouter(tags=["ai"])


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_endpoint(
    audio: UploadFile | None = File(default=None),
    text_override: str | None = Form(default=None),
    _: AuthContext = Depends(get_current_auth_context),
) -> TranscribeResponse:
    try:
        transcript, mode = await transcribe(audio=audio, text_override=text_override)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        if getattr(exc, "status_code", None) == 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported or invalid audio file. Use wav, mp3, mp4, m4a, ogg, or webm.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Audio transcription failed via OpenAI API.",
        ) from exc
    return TranscribeResponse(transcript=transcript, mode=mode)


@router.post("/extract-intake", response_model=StructuredIntake)
def extract_intake(
    payload: ExtractIntakeRequest,
    _: AuthContext = Depends(get_current_auth_context),
) -> StructuredIntake:
    return extract_structured_intake(payload.transcript)


@router.post("/decision-support", response_model=DecisionSupportOutput)
def decision_support(
    payload: DecisionSupportRequest,
    current: AuthContext = Depends(get_current_auth_context),
    db: Session = Depends(get_db),
) -> DecisionSupportOutput:
    query_text = f"{payload.transcript}\nSymptoms: {', '.join(payload.structured_intake.symptoms)}"
    retrieved = retrieve_chunks(db, query_text=query_text, specialty=payload.specialty)
    retrieved_payload = [
        {
            "chunk_id": r.chunk_id,
            "title": r.title,
            "source": r.source,
            "excerpt": r.excerpt,
            "score": r.fused_score,
        }
        for r in retrieved
    ]
    try:
        output = generate_decision_support(payload.transcript, payload.specialty, retrieved_payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Decision support generation failed via OpenAI API.",
        ) from exc

    if payload.encounter_id:
        encounter = db.execute(
            select(Encounter).where(
                Encounter.id == payload.encounter_id,
                Encounter.organization_id == current.organization.id,
            )
        ).scalar_one_or_none()
        if not encounter:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")

        row = AIOutput(
            encounter_id=payload.encounter_id,
            model_version="openai-gpt-4.1-mini",
            specialty_used=payload.specialty,
            differential_json=[i.model_dump() for i in output.differential],
            red_flags_json=[i.model_dump() for i in output.red_flags],
            followups_json=[i.model_dump() for i in output.followups],
            tests_json=[i.model_dump() for i in output.tests],
            citations_json=[i.model_dump() for i in output.citations],
            confidence=output.confidence,
            uncertainty_notes=output.uncertainty_notes,
        )
        db.add(row)
        db.flush()
        log_action(
            db,
            organization_id=current.organization.id,
            actor_clinician_id=current.clinician.id,
            entity_type="ai_output",
            entity_id=row.id,
            action="generate_decision_support",
            before_json=None,
            after_json={"encounter_id": payload.encounter_id, "specialty": payload.specialty},
        )
        db.commit()

    return output
