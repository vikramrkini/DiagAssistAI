from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_clinician
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.clinician import Clinician
from app.schemas.auth import AuthTokenResponse, LoginRequest, MeResponse, SignUpRequest
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthTokenResponse)
def signup(payload: SignUpRequest, response: Response, db: Session = Depends(get_db)) -> AuthTokenResponse:
    existing = db.execute(select(Clinician).where(Clinician.email == payload.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    clinician = Clinician(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        specialty=payload.specialty,
    )
    db.add(clinician)
    db.flush()

    log_action(
        db,
        actor_clinician_id=clinician.id,
        entity_type="clinician",
        entity_id=clinician.id,
        action="signup",
        before_json=None,
        after_json={"email": clinician.email, "specialty": clinician.specialty},
    )

    token = create_access_token(payload.email, clinician.id)
    db.commit()
    response.set_cookie("diagassist_token", token, httponly=True, samesite="lax")
    return AuthTokenResponse(access_token=token)


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthTokenResponse:
    clinician = db.execute(select(Clinician).where(Clinician.email == payload.email)).scalar_one_or_none()
    if not clinician or not verify_password(payload.password, clinician.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(clinician.email, clinician.id)
    response.set_cookie("diagassist_token", token, httponly=True, samesite="lax")
    return AuthTokenResponse(access_token=token)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie("diagassist_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=MeResponse)
def me(current: Clinician = Depends(get_current_clinician)) -> MeResponse:
    return MeResponse(id=current.id, email=current.email, name=current.name, specialty=current.specialty)
