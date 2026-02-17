from pathlib import Path

from fastapi import UploadFile
from openai import OpenAI

from app.core.config import settings

DEMO_TRANSCRIPT_PATH = Path("/workspace/data/eval/demo_transcript.txt")


async def transcribe(audio: UploadFile | None, text_override: str | None) -> tuple[str, str]:
    if text_override:
        return text_override, "text_override"

    if audio and settings.openai_api_key:
        client = OpenAI(api_key=settings.openai_api_key)
        payload = await audio.read()
        with open("/tmp/diagassist_audio_input", "wb") as f:
            f.write(payload)
        with open("/tmp/diagassist_audio_input", "rb") as f:
            resp = client.audio.transcriptions.create(model="whisper-1", file=f)
            return resp.text, "openai_whisper"

    if DEMO_TRANSCRIPT_PATH.exists():
        return DEMO_TRANSCRIPT_PATH.read_text().strip(), "demo_fixture"

    return (
        "Patient reports fever for three days, sore throat, mild cough, and reduced appetite. No chest pain or shortness of breath.",
        "demo_fallback",
    )
