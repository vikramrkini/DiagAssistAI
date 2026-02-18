from fastapi import UploadFile
from openai import OpenAI

from app.core.config import settings

async def transcribe(audio: UploadFile | None, text_override: str | None) -> tuple[str, str]:
    if text_override:
        return text_override, "text_override"

    if not audio:
        raise ValueError("Provide either audio or text_override.")
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for audio transcription.")

    client = OpenAI(api_key=settings.openai_api_key)
    payload = await audio.read()
    with open("/tmp/diagassist_audio_input", "wb") as f:
        f.write(payload)
    with open("/tmp/diagassist_audio_input", "rb") as f:
        resp = client.audio.transcriptions.create(model="whisper-1", file=f)
    return resp.text, "openai_whisper"
