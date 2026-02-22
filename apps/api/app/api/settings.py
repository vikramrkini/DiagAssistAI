from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, get_current_auth_context
from app.core.config import settings
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
def get_settings(_: AuthContext = Depends(get_current_auth_context)) -> AppSettingsOut:
    return AppSettingsOut(
        store_audio=_demo_store["store_audio"],
        openai_key_configured=bool(settings.openai_api_key),
        specialty_depth=_demo_store["specialty_depth"],
    )


@router.put("", response_model=AppSettingsOut)
def update_settings(payload: AppSettingsUpdate, _: AuthContext = Depends(get_current_auth_context)) -> AppSettingsOut:
    updates = payload.model_dump(exclude_none=True)
    _demo_store.update(updates)
    return AppSettingsOut(
        store_audio=_demo_store["store_audio"],
        openai_key_configured=bool(settings.openai_api_key),
        specialty_depth=_demo_store["specialty_depth"],
    )
