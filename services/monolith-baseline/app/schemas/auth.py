from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserInfo(BaseModel):
    user_id: str
    email: str
    full_name: str = ""


class TokenResponse(BaseModel):
    token: str
    expires_in: int = 86400
    user: UserInfo


class RegistrationResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    created_at: datetime


class JWTPayload(BaseModel):
    user_id: str
    email: str
    iat: int
    exp: int
