from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AccountLockedError, InvalidCredentialsError, RateLimitExceededError
from app.core.security import hash_password
from app.models.credential import UserCredential
from app.schemas.auth import TokenResponse
from app.services.auth_service import AuthService


def _make_service():
    svc = AuthService(MagicMock())
    svc._credentials = AsyncMock()
    svc._blocklist = AsyncMock()
    svc._recovery = AsyncMock()
    return svc


def _credential(status: str = "active") -> MagicMock:
    cred = MagicMock(spec=UserCredential)
    cred.user_id = "user-abc"
    cred.password_hash = hash_password("correct_pass")
    cred.account_status = status
    return cred


async def test_login_valid_credentials_returns_token():
    svc = _make_service()
    svc._credentials.get_by_email.return_value = _credential()

    result = await svc.login("user@example.com", "correct_pass")

    assert isinstance(result, TokenResponse)
    assert result.token
    assert result.user.user_id == "user-abc"
    assert result.user.email == "user@example.com"


async def test_login_wrong_password_raises_401():
    svc = _make_service()
    svc._credentials.get_by_email.return_value = _credential()

    with pytest.raises(InvalidCredentialsError):
        await svc.login("user@example.com", "wrong_pass")


async def test_login_unknown_email_raises_401():
    svc = _make_service()
    svc._credentials.get_by_email.return_value = None

    with pytest.raises(InvalidCredentialsError):
        await svc.login("nobody@example.com", "any_pass")


async def test_login_locked_account_raises_403():
    svc = _make_service()
    svc._credentials.get_by_email.return_value = _credential(status="locked")

    with pytest.raises(AccountLockedError):
        await svc.login("user@example.com", "correct_pass")


async def test_login_disabled_account_raises_403():
    svc = _make_service()
    svc._credentials.get_by_email.return_value = _credential(status="disabled")

    with pytest.raises(AccountLockedError):
        await svc.login("user@example.com", "correct_pass")


async def test_login_rate_limit_exceeded_raises_429():
    svc = _make_service()

    with patch("app.services.auth_service.rate_limiter") as mock_rl:
        mock_rl.is_blocked.return_value = True

        with pytest.raises(RateLimitExceededError):
            await svc.login("user@example.com", "any_pass")

        mock_rl.is_blocked.assert_called_once_with("user@example.com")
        svc._credentials.get_by_email.assert_not_called()


async def test_login_failure_records_rate_limit_hit():
    svc = _make_service()
    svc._credentials.get_by_email.return_value = _credential()

    with patch("app.services.auth_service.rate_limiter") as mock_rl:
        mock_rl.is_blocked.return_value = False

        with pytest.raises(InvalidCredentialsError):
            await svc.login("user@example.com", "wrong_pass")

        mock_rl.record_failure.assert_called_once_with("user@example.com")


async def test_login_success_resets_rate_limiter():
    svc = _make_service()
    svc._credentials.get_by_email.return_value = _credential()

    with patch("app.services.auth_service.rate_limiter") as mock_rl:
        mock_rl.is_blocked.return_value = False

        await svc.login("user@example.com", "correct_pass")

        mock_rl.reset.assert_called_once_with("user@example.com")
