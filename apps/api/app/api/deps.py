from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.clinician import Clinician

bearer = HTTPBearer(auto_error=False)


def get_token_from_request(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str | None:
    if creds:
        return creds.credentials
    cookie_token = request.cookies.get("diagassist_token")
    return cookie_token


def get_current_clinician(
    db: Session = Depends(get_db),
    token: str | None = Depends(get_token_from_request),
) -> Clinician:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

    clinician_id = payload.get("clinician_id")
    clinician = db.get(Clinician, clinician_id)
    if not clinician:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clinician not found")
    return clinician
