from pydantic import BaseModel, Field

from app.schemas.email import AppEmail


class SignUpRequest(BaseModel):
    email: AppEmail
    password: str = Field(min_length=8)
    name: str = Field(min_length=2)
    specialty: str = Field(default="general")


class LoginRequest(BaseModel):
    email: AppEmail
    password: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    email: AppEmail
    name: str
    specialty: str
