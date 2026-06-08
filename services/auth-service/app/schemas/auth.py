from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserInfo(BaseModel):
    user_id: str
    email: str
    full_name: str


class TokenResponse(BaseModel):
    token: str
    expires_in: int = 86400
    user: UserInfo


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ---------- Internal (service-to-service) ----------

class CreateCredentialRequest(BaseModel):
    user_id: str
    email: EmailStr
    password_hash: str


class ValidateTokenRequest(BaseModel):
    token: str


class ValidateTokenResponse(BaseModel):
    valid: bool
    user_id: str = ""
    email: str = ""
    expires_at: str = ""


class BlocklistTokenRequest(BaseModel):
    token: str
    expires_at: str  # ISO 8601


# ---------- JWT payload ----------

class JWTPayload(BaseModel):
    user_id: str
    email: str
    iat: int
    exp: int
