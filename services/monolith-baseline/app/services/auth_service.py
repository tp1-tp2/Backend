"""Trimmed from auth-service's AuthService + user-service's UserService register
flow. Since everything runs in one process, register no longer needs the
cross-service HTTP call that user-service made to auth-service — it's a single
local transaction creating both the profile and credential rows. Password
recovery, email confirmation and email-change flows are out of scope for this
baseline (E3/E4/E6 only exercise register -> login -> transcribe -> list).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmailAlreadyExistsError, InvalidCredentialsError, TokenInvalidError
from app.core.security import decode_jwt, generate_jwt, hash_password, hash_token, verify_password
from app.models.credential import TokenBlocklist, UserCredential
from app.models.user import UserProfile
from app.schemas.auth import RegistrationResponse, TokenResponse, UserInfo


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, email: str, password: str, full_name: str) -> RegistrationResponse:
        existing = await self._session.scalar(select(UserCredential).where(UserCredential.email == email))
        if existing:
            raise EmailAlreadyExistsError()

        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        profile = UserProfile(
            user_id=user_id, email=email, full_name=full_name, created_at=now, updated_at=now
        )
        credential = UserCredential(
            user_id=user_id,
            email=email,
            password_hash=hash_password(password),
            account_status="active",
            created_at=now,
            updated_at=now,
        )
        self._session.add_all([profile, credential])
        await self._session.commit()

        return RegistrationResponse(user_id=user_id, email=email, full_name=full_name, created_at=now)

    async def login(self, email: str, password: str) -> TokenResponse:
        credential = await self._session.scalar(select(UserCredential).where(UserCredential.email == email))
        if not credential or not verify_password(password, credential.password_hash):
            raise InvalidCredentialsError()

        token = generate_jwt(credential.user_id, email)
        return TokenResponse(token=token, user=UserInfo(user_id=credential.user_id, email=email))

    async def logout(self, token: str) -> None:
        payload = decode_jwt(token)
        token_hash = hash_token(token)
        expires_at = datetime.fromtimestamp(payload.exp, tz=timezone.utc)
        self._session.add(
            TokenBlocklist(
                token_hash=token_hash,
                user_id=payload.user_id,
                expires_at=expires_at,
                blocked_at=datetime.now(timezone.utc),
            )
        )
        await self._session.commit()

    async def validate_token(self, token: str) -> dict:
        payload = decode_jwt(token)  # raises TokenInvalidError if malformed/expired
        blocked = await self._session.scalar(
            select(TokenBlocklist).where(TokenBlocklist.token_hash == hash_token(token))
        )
        if blocked:
            raise TokenInvalidError("Token has been revoked")
        return {"user_id": payload.user_id, "email": payload.email}
