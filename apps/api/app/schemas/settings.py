from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    store_audio: bool
    openai_key_configured: bool
    specialty_depth: dict


class AppSettingsUpdate(BaseModel):
    store_audio: bool | None = None
    specialty_depth: dict | None = None
