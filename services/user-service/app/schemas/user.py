import re
from datetime import date, datetime, timezone
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


def _validate_phone(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    if not _E164_RE.match(v):
        raise ValueError("Phone number must be in E.164 format (e.g. +51987654321)")
    return v


def _validate_age(v: Optional[date]) -> Optional[date]:
    if v is None:
        return v
    today = date.today()
    age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
    if age < 13:
        raise ValueError("User must be at least 13 years old")
    return v


# ---------- Public request/response schemas ----------

class RegistrationRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)


class RegistrationResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone(v)

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: Optional[date]) -> Optional[date]:
        return _validate_age(v)


class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Internal (service-to-service) ----------

class InternalUserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    account_status: str = "active"

    model_config = {"from_attributes": True}


# ---------- Email change ----------

class EmailChangeRequestSchema(BaseModel):
    new_email: EmailStr


class EmailChangeVerifyRequest(BaseModel):
    token: str
    link_type: str  # "old" | "new"
