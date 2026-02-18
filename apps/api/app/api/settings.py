from fastapi import APIRouter, Depends

from app.api.deps import get_current_clinician
from app.core.config import settings
from app.models.clinician import Clinician
from app.schemas.settings import AppSettingsOut, AppSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

_demo_store = {
    "store_audio": settings.store_audio,
    "specialty_depth": {
        "general": "medium",
        "pediatrics": "conservative",
        "physiotherapy": "focused",
        "dermatology": "focused",
    },
}


@router.get("", response_model=AppSettingsOut)
def get_settings(_: Clinician = Depends(get_current_clinician)) -> AppSettingsOut:
    return AppSettingsOut(
        store_audio=_demo_store["store_audio"],
        openai_key_configured=bool(settings.openai_api_key),
        specialty_depth=_demo_store["specialty_depth"],
    )


@router.put("", response_model=AppSettingsOut)
def update_settings(payload: AppSettingsUpdate, _: Clinician = Depends(get_current_clinician)) -> AppSettingsOut:
    updates = payload.model_dump(exclude_none=True)
    _demo_store.update(updates)
    return AppSettingsOut(
        store_audio=_demo_store["store_audio"],
        openai_key_configured=bool(settings.openai_api_key),
        specialty_depth=_demo_store["specialty_depth"],
    )
