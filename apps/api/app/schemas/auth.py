from pydantic import BaseModel, Field, model_validator

from app.schemas.email import AppEmail


class SignUpRequest(BaseModel):
    email: AppEmail
    password: str = Field(min_length=8)
    name: str = Field(min_length=2)
    specialty: str = Field(default="general")
    account_type: str = Field(default="private_practice")
    organization_name: str | None = Field(default=None, min_length=2)
    hospital_invite_code: str | None = Field(default=None, min_length=6)

    @model_validator(mode="after")
    def validate_org_fields(self) -> "SignUpRequest":
        account_type = (self.account_type or "").strip()
        if account_type not in {"private_practice", "hospital"}:
            raise ValueError("account_type must be 'private_practice' or 'hospital'")
        if self.hospital_invite_code and account_type != "hospital":
            raise ValueError("hospital_invite_code can only be used with account_type='hospital'")
        if account_type == "hospital" and not self.organization_name and not self.hospital_invite_code:
            raise ValueError("For hospital signup, provide organization_name or hospital_invite_code")
        return self


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
    organization_id: int
    organization_name: str
    organization_type: str
    role: str
    hospital_invite_code: str | None = None
