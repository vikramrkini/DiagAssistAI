import os
import tempfile

from fastapi import UploadFile
from openai import OpenAI

from app.core.config import settings


_MIME_TO_SUFFIX = {
    "audio/flac": ".flac",
    "audio/mp4": ".mp4",
    "audio/mpeg": ".mp3",
    "audio/mpga": ".mpga",
    "audio/ogg": ".ogg",
    "audio/oga": ".oga",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/webm": ".webm",
    "video/webm": ".webm",
}


def _infer_audio_suffix(audio: UploadFile) -> str:
    filename = audio.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext:
        return ext
    return _MIME_TO_SUFFIX.get((audio.content_type or "").lower(), ".webm")


async def transcribe(audio: UploadFile | None, text_override: str | None) -> tuple[str, str]:
    if text_override:
        return text_override, "text_override"

    if not audio:
        raise ValueError("Provide either audio or text_override.")
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for audio transcription.")

    client = OpenAI(api_key=settings.openai_api_key)
    payload = await audio.read()
    if not payload:
        raise ValueError("Uploaded audio file is empty.")

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=_infer_audio_suffix(audio)) as tmp:
            tmp.write(payload)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            resp = client.audio.transcriptions.create(model="whisper-1", file=f)
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    return resp.text, "openai_whisper"
