from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    demo_mode: bool
    store_audio: bool
    openai_key_configured: bool
    specialty_depth: dict


class AppSettingsUpdate(BaseModel):
    demo_mode: bool | None = None
    store_audio: bool | None = None
    specialty_depth: dict | None = None
