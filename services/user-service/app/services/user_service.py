import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.email import send_confirmation, send_verification_link
from app.core.exceptions import EmailAlreadyExistsError, UserNotFoundError
from app.db.repositories import EmailChangeRepository, UserRepository
from app.schemas.user import (
    EmailChangeVerifyRequest,
    RegistrationResponse,
    UpdateProfileRequest,
    UserResponse,
)

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, session: AsyncSession, http_client: httpx.AsyncClient) -> None:
        self._users = UserRepository(session)
        self._email_changes = EmailChangeRepository(session)
        self._http = http_client

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> RegistrationResponse:
        if await self._users.get_by_email(email):
            raise EmailAlreadyExistsError()

        user_id = str(uuid.uuid4())
        profile = await self._users.create(user_id, email, full_name)

        try:
            resp = await self._http.post(
                f"{settings.auth_service_url}/internal/auth/credentials",
                json={"user_id": user_id, "email": email, "password": password},
                timeout=settings.email_confirmation_timeout_seconds,
            )
            resp.raise_for_status()
        except Exception as exc:
            # Roll back profile if auth credential creation fails
            await self._users.update(user_id)  # soft approach: mark or delete
            logger.error("Auth credential creation failed for %s: %s", user_id, exc)
            raise

        if background_tasks:
            background_tasks.add_task(send_confirmation, email, user_id)
        else:
            await send_confirmation(email, user_id)

        return RegistrationResponse(
            user_id=profile.user_id,
            email=profile.email,
            full_name=profile.full_name,
            created_at=profile.created_at,
        )

    async def get_profile(self, user_id: str) -> UserResponse:
        profile = await self._users.get_by_id(user_id)
        if not profile:
            raise UserNotFoundError()
        return UserResponse.model_validate(profile)

    async def update_profile(
        self, user_id: str, data: UpdateProfileRequest
    ) -> UserResponse:
        profile = await self._users.get_by_id(user_id)
        if not profile:
            raise UserNotFoundError()

        fields = data.model_dump(exclude_none=True)
        if not fields:
            return UserResponse.model_validate(profile)

        updated = await self._users.update(user_id, **fields)
        return UserResponse.model_validate(updated)

    async def initiate_email_change(
        self,
        user_id: str,
        new_email: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> None:
        profile = await self._users.get_by_id(user_id)
        if not profile:
            raise UserNotFoundError()

        if await self._users.get_by_email(new_email):
            raise EmailAlreadyExistsError()

        # Cancel any pending request for this user
        await self._email_changes.delete_by_user(user_id)

        request_id = str(uuid.uuid4())
        old_token = str(uuid.uuid4())
        new_token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.email_change_expiry_hours
        )

        await self._email_changes.create(
            request_id=request_id,
            user_id=user_id,
            old_email=profile.email,
            new_email=new_email,
            old_email_token=old_token,
            new_email_token=new_token,
            expires_at=expires_at,
        )

        if background_tasks:
            background_tasks.add_task(send_verification_link, profile.email, old_token, "old")
            background_tasks.add_task(send_verification_link, new_email, new_token, "new")
        else:
            await send_verification_link(profile.email, old_token, "old")
            await send_verification_link(new_email, new_token, "new")

    async def verify_email_change(self, token: str, link_type: str) -> None:
        if link_type == "old":
            entry = await self._email_changes.get_by_old_token(token)
        else:
            entry = await self._email_changes.get_by_new_token(token)

        if not entry:
            from app.core.exceptions import ValidationError
            raise ValidationError("token", "invalid or expired")

        if link_type == "old":
            await self._email_changes.mark_old_verified(entry.request_id)
        else:
            await self._email_changes.mark_new_verified(entry.request_id)

        # Reload to check both sides
        entry = await self._email_changes.get_by_user(entry.user_id)
        if entry and entry.old_email_verified and entry.new_email_verified:
            await self._users.update(entry.user_id, email=entry.new_email)
            await self._email_changes.delete_by_user(entry.user_id)
