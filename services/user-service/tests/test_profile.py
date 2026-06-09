from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.exceptions import UserNotFoundError
from app.models.user import UserProfile
from app.schemas.user import UpdateProfileRequest, UserResponse
from app.services.user_service import UserService


def _make_service() -> UserService:
    svc = UserService(MagicMock(), AsyncMock(spec=httpx.AsyncClient))
    svc._users = AsyncMock()
    svc._email_changes = AsyncMock()
    return svc


def _profile(
    user_id: str = "uid-1",
    email: str = "user@example.com",
    full_name: str = "Ada Lovelace",
    phone_number: str | None = None,
    date_of_birth: date | None = None,
) -> MagicMock:
    p = MagicMock(spec=UserProfile)
    p.user_id = user_id
    p.email = email
    p.full_name = full_name
    p.phone_number = phone_number
    p.date_of_birth = date_of_birth
    p.created_at = datetime.now(timezone.utc)
    p.updated_at = datetime.now(timezone.utc)
    return p


# ---------- get_profile ----------

async def test_get_profile_returns_user_response():
    svc = _make_service()
    svc._users.get_by_id.return_value = _profile()

    result = await svc.get_profile("uid-1")

    assert isinstance(result, UserResponse)
    assert result.user_id == "uid-1"
    assert result.email == "user@example.com"


async def test_get_profile_not_found_raises():
    svc = _make_service()
    svc._users.get_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        await svc.get_profile("nonexistent")


# ---------- update_profile ----------

async def test_update_profile_full_name():
    svc = _make_service()
    original = _profile()
    updated = _profile(full_name="Grace Hopper")
    svc._users.get_by_id.return_value = original
    svc._users.update.return_value = updated

    result = await svc.update_profile("uid-1", UpdateProfileRequest(full_name="Grace Hopper"))

    svc._users.update.assert_called_once()
    assert result.full_name == "Grace Hopper"


async def test_update_profile_valid_phone():
    svc = _make_service()
    original = _profile()
    updated = _profile(phone_number="+51987654321")
    svc._users.get_by_id.return_value = original
    svc._users.update.return_value = updated

    result = await svc.update_profile(
        "uid-1", UpdateProfileRequest(phone_number="+51987654321")
    )

    assert result.phone_number == "+51987654321"


async def test_update_profile_invalid_phone_rejected_by_schema():
    with pytest.raises(Exception):
        UpdateProfileRequest(phone_number="0987654321")  # missing + prefix


async def test_update_profile_underage_dob_rejected_by_schema():
    with pytest.raises(Exception):
        UpdateProfileRequest(date_of_birth=date(2020, 1, 1))  # < 13 years old


async def test_update_profile_valid_adult_dob():
    svc = _make_service()
    dob = date(1990, 6, 15)
    original = _profile()
    updated = _profile(date_of_birth=dob)
    svc._users.get_by_id.return_value = original
    svc._users.update.return_value = updated

    result = await svc.update_profile(
        "uid-1", UpdateProfileRequest(date_of_birth=dob)
    )

    assert result.date_of_birth == dob


async def test_update_profile_no_fields_skips_db_write():
    svc = _make_service()
    original = _profile()
    svc._users.get_by_id.return_value = original

    result = await svc.update_profile("uid-1", UpdateProfileRequest())

    svc._users.update.assert_not_called()
    assert result.user_id == "uid-1"


async def test_update_profile_user_not_found_raises():
    svc = _make_service()
    svc._users.get_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        await svc.update_profile("ghost", UpdateProfileRequest(full_name="X"))
