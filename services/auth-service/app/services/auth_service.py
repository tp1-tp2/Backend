import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AccountLockedError,
    InvalidCredentialsError,
    RateLimitExceededError,
    TokenInvalidError,
)
from app.core.security import (
    decode_jwt,
    generate_jwt,
    generate_recovery_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.repositories import BlocklistRepository, CredentialRepository, RecoveryRepository
from app.schemas.auth import TokenResponse, UserInfo, ValidateTokenResponse
from app.services.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._credentials = CredentialRepository(session)
        self._blocklist = BlocklistRepository(session)
        self._recovery = RecoveryRepository(session)

    async def login(self, email: str, password: str) -> TokenResponse:
        if rate_limiter.is_blocked(email):
            raise RateLimitExceededError()

        credential = await self._credentials.get_by_email(email)
        if not credential or not verify_password(password, credential.password_hash):
            rate_limiter.record_failure(email)
            raise InvalidCredentialsError()

        if credential.account_status in ("locked", "disabled"):
            raise AccountLockedError()

        rate_limiter.reset(email)
        token = generate_jwt(credential.user_id, email)
        return TokenResponse(
            token=token,
            expires_in=settings.jwt_expiration_hours * 3600,
            user=UserInfo(user_id=credential.user_id, email=email),
        )

    async def logout(self, token: str) -> None:
        payload = decode_jwt(token)
        token_hash = hash_token(token)
        expires_at = datetime.fromtimestamp(payload.exp, tz=timezone.utc)
        await self._blocklist.add(token_hash, payload.user_id, expires_at)

    async def validate_token(self, token: str) -> ValidateTokenResponse:
        try:
            payload = decode_jwt(token)
        except TokenInvalidError:
            return ValidateTokenResponse(valid=False)

        if await self._blocklist.exists(hash_token(token)):
            return ValidateTokenResponse(valid=False)

        return ValidateTokenResponse(
            valid=True,
            user_id=payload.user_id,
            email=payload.email,
            expires_at=datetime.fromtimestamp(payload.exp, tz=timezone.utc).isoformat(),
        )

    async def blocklist_token(self, token: str, expires_at_iso: str) -> None:
        try:
            payload = decode_jwt(token)
        except TokenInvalidError:
            # Token is already invalid; still store the hash in case it's a known-bad token
            payload = None

        token_hash = hash_token(token)
        expires_at = datetime.fromisoformat(expires_at_iso)
        user_id = payload.user_id if payload else ""
        await self._blocklist.add(token_hash, user_id, expires_at)

    async def create_credential(
        self, user_id: str, email: str, password_hash: str
    ) -> None:
        await self._credentials.create(user_id, email, password_hash)

    async def initiate_recovery(self, email: str) -> None:
        credential = await self._credentials.get_by_email(email)
        if not credential:
            # Never reveal whether the email is registered
            return

        token = generate_recovery_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.recovery_token_expiry_hours
        )
        await self._recovery.create(token, credential.user_id, email, expires_at)

        # TODO: replace with actual email service (SMTP / SendGrid)
        logger.info(
            "Password recovery token for %s: %s (expires %s)",
            email,
            token,
            expires_at.isoformat(),
        )

    async def reset_password(self, token: str, new_password: str) -> None:
        entry = await self._recovery.get_valid(token)
        if not entry:
            raise TokenInvalidError("Recovery token is invalid or has expired")

        await self._credentials.update_password(entry.user_id, hash_password(new_password))
        await self._recovery.mark_used(token)

    async def cleanup_expired_tokens(self) -> int:
        deleted = await self._blocklist.delete_expired()
        logger.info("Cleaned up %d expired blocklist tokens", deleted)
        return deleted
