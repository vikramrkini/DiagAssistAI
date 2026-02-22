from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai, auth, clinicians, encounters, patients, settings as settings_api
from app.api.deps import AuthContext, get_current_auth_context
from app.core.config import settings

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
def me(current: AuthContext = Depends(get_current_auth_context)) -> dict:
    return {
        "id": current.clinician.id,
        "email": current.clinician.email,
        "name": current.clinician.name,
        "specialty": current.clinician.specialty,
        "organization_id": current.organization.id,
        "organization_name": current.organization.name,
        "organization_type": current.organization.org_type,
        "role": current.membership.role,
    }
