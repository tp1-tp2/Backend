from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.exceptions import EmailAlreadyExistsError
from app.models.user import UserProfile
from app.schemas.user import RegistrationResponse
from app.services.user_service import UserService


def _make_service(auth_status: int = 201) -> UserService:
    session = MagicMock()
    http_client = AsyncMock(spec=httpx.AsyncClient)
    mock_resp = MagicMock()
    mock_resp.status_code = auth_status
    mock_resp.raise_for_status = MagicMock(
        side_effect=None if auth_status < 400 else httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_resp
        )
    )
    http_client.post.return_value = mock_resp

    svc = UserService(session, http_client)
    svc._users = AsyncMock()
    svc._email_changes = AsyncMock()
    return svc


def _profile(user_id: str = "uid-1", email: str = "user@example.com") -> MagicMock:
    p = MagicMock(spec=UserProfile)
    p.user_id = user_id
    p.email = email
    p.full_name = "Test User"
    p.created_at = datetime.now(timezone.utc)
    return p


async def test_register_new_user_returns_response():
    svc = _make_service()
    svc._users.get_by_email.return_value = None
    svc._users.create.return_value = _profile()

    result = await svc.register("user@example.com", "password123", "Test User")

    assert isinstance(result, RegistrationResponse)
    assert result.email == "user@example.com"
    assert result.full_name == "Test User"
    assert result.user_id


async def test_register_calls_auth_service():
    svc = _make_service()
    svc._users.get_by_email.return_value = None
    svc._users.create.return_value = _profile()

    await svc.register("user@example.com", "pass12345", "Test User")

    svc._http.post.assert_called_once()
    call_kwargs = svc._http.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1] if len(call_kwargs.args) > 1 else call_kwargs.kwargs["json"]
    assert payload["email"] == "user@example.com"
    assert "password" in payload
    assert "user_id" in payload


async def test_register_duplicate_email_raises():
    svc = _make_service()
    svc._users.get_by_email.return_value = _profile()

    with pytest.raises(EmailAlreadyExistsError):
        await svc.register("user@example.com", "pass12345", "Test User")

    svc._users.create.assert_not_called()
    svc._http.post.assert_not_called()


async def test_register_auth_service_failure_propagates():
    svc = _make_service(auth_status=500)
    svc._users.get_by_email.return_value = None
    svc._users.create.return_value = _profile()

    with pytest.raises(Exception):
        await svc.register("user@example.com", "pass12345", "Test User")


async def test_register_password_not_stored_in_profile():
    """User profile must never contain the plain-text password."""
    svc = _make_service()
    svc._users.get_by_email.return_value = None
    svc._users.create.return_value = _profile()

    result = await svc.register("user@example.com", "secret_pass", "Test User")

    create_call = svc._users.create.call_args
    # create(user_id, email, full_name) — password must NOT appear
    assert "secret_pass" not in str(create_call)
    assert not hasattr(result, "password")
