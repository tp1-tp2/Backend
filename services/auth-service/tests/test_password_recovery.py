from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import TokenInvalidError
from app.core.security import verify_password
from app.models.credential import PasswordRecoveryToken
from app.services.auth_service import AuthService


def _make_service():
    svc = AuthService(MagicMock())
    svc._credentials = AsyncMock()
    svc._blocklist = AsyncMock()
    svc._recovery = AsyncMock()
    return svc


def _recovery_entry(used: bool = False, expired: bool = False) -> MagicMock:
    entry = MagicMock(spec=PasswordRecoveryToken)
    entry.user_id = "user-xyz"
    entry.email = "user@example.com"
    entry.used = used
    entry.expires_at = (
        datetime.now(timezone.utc) - timedelta(hours=2)
        if expired
        else datetime.now(timezone.utc) + timedelta(hours=1)
    )
    return entry


async def test_initiate_recovery_creates_token_for_known_email():
    svc = _make_service()
    svc._credentials.get_by_email.return_value = MagicMock(
        user_id="user-xyz", account_status="active"
    )

    await svc.initiate_recovery("user@example.com")

    svc._recovery.create.assert_called_once()
    call_args = svc._recovery.create.call_args
    assert call_args.args[1] == "user-xyz"
    assert call_args.args[2] == "user@example.com"


async def test_initiate_recovery_unknown_email_is_silent():
    """Must not raise or leak whether the email is registered."""
    svc = _make_service()
    svc._credentials.get_by_email.return_value = None

    await svc.initiate_recovery("nobody@example.com")

    svc._recovery.create.assert_not_called()


async def test_reset_password_valid_token_updates_hash():
    svc = _make_service()
    svc._recovery.get_valid.return_value = _recovery_entry()

    await svc.reset_password("valid_token_xyz", "NewPass123!")

    svc._credentials.update_password.assert_called_once()
    call_args = svc._credentials.update_password.call_args
    assert call_args.args[0] == "user-xyz"
    new_hash = call_args.args[1]
    assert verify_password("NewPass123!", new_hash)


async def test_reset_password_marks_token_used():
    svc = _make_service()
    svc._recovery.get_valid.return_value = _recovery_entry()

    await svc.reset_password("valid_token_xyz", "NewPass123!")

    svc._recovery.mark_used.assert_called_once_with("valid_token_xyz")


async def test_reset_password_invalid_token_raises():
    svc = _make_service()
    svc._recovery.get_valid.return_value = None

    with pytest.raises(TokenInvalidError):
        await svc.reset_password("bad_token", "NewPass123!")

    svc._credentials.update_password.assert_not_called()


async def test_reset_password_expired_token_raises():
    """get_valid returns None for expired tokens (repo filters them out)."""
    svc = _make_service()
    svc._recovery.get_valid.return_value = None

    with pytest.raises(TokenInvalidError):
        await svc.reset_password("expired_token", "NewPass123!")
