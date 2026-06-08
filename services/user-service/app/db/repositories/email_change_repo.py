from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import EmailChangeRequest


class EmailChangeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        request_id: str,
        user_id: str,
        old_email: str,
        new_email: str,
        old_email_token: str,
        new_email_token: str,
        expires_at: datetime,
    ) -> EmailChangeRequest:
        entry = EmailChangeRequest(
            request_id=request_id,
            user_id=user_id,
            old_email=old_email,
            new_email=new_email,
            old_email_token=old_email_token,
            new_email_token=new_email_token,
            expires_at=expires_at,
            old_email_verified=False,
            new_email_verified=False,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def get_by_user(self, user_id: str) -> EmailChangeRequest | None:
        result = await self._session.execute(
            select(EmailChangeRequest)
            .where(
                EmailChangeRequest.user_id == user_id,
                EmailChangeRequest.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_old_token(self, token: str) -> EmailChangeRequest | None:
        result = await self._session.execute(
            select(EmailChangeRequest).where(EmailChangeRequest.old_email_token == token)
        )
        return result.scalar_one_or_none()

    async def get_by_new_token(self, token: str) -> EmailChangeRequest | None:
        result = await self._session.execute(
            select(EmailChangeRequest).where(EmailChangeRequest.new_email_token == token)
        )
        return result.scalar_one_or_none()

    async def mark_old_verified(self, request_id: str) -> None:
        await self._session.execute(
            update(EmailChangeRequest)
            .where(EmailChangeRequest.request_id == request_id)
            .values(old_email_verified=True)
        )
        await self._session.commit()

    async def mark_new_verified(self, request_id: str) -> None:
        await self._session.execute(
            update(EmailChangeRequest)
            .where(EmailChangeRequest.request_id == request_id)
            .values(new_email_verified=True)
        )
        await self._session.commit()

    async def delete_by_user(self, user_id: str) -> None:
        await self._session.execute(
            delete(EmailChangeRequest).where(EmailChangeRequest.user_id == user_id)
        )
        await self._session.commit()

    async def cancel_expired(self) -> int:
        result = await self._session.execute(
            delete(EmailChangeRequest).where(
                EmailChangeRequest.expires_at < datetime.now(timezone.utc)
            )
        )
        await self._session.commit()
        return result.rowcount
