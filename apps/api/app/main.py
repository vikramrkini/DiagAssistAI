from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai, auth, clinicians, encounters, patients, settings as settings_api
from app.api.deps import get_current_clinician
from app.core.config import settings
from app.models.clinician import Clinician

app = FastAPI(title="DiagAssistAI API", version="0.1.0")

origins = [x.strip() for x in settings.web_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clinicians.router)
app.include_router(patients.router)
app.include_router(encounters.router)
app.include_router(ai.router)
app.include_router(settings_api.router)


@app.get("/")
def root() -> dict:
    return {
        "name": "DiagAssistAI API",
        "disclaimer": "Educational demo; not for real clinical use.",
        "decision_support_notice": "Decision support only. Final diagnosis must be clinician-confirmed.",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/me")
def me(current: Clinician = Depends(get_current_clinician)) -> dict:
    return {
        "id": current.id,
        "email": current.email,
        "name": current.name,
        "specialty": current.specialty,
    }
