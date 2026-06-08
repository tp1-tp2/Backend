from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import UserCredential


class CredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> UserCredential | None:
        result = await self._session.execute(
            select(UserCredential).where(UserCredential.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> UserCredential | None:
        result = await self._session.execute(
            select(UserCredential).where(UserCredential.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: str, email: str, password_hash: str) -> UserCredential:
        now = datetime.now(timezone.utc)
        credential = UserCredential(
            user_id=user_id,
            email=email,
            password_hash=password_hash,
            account_status="active",
            created_at=now,
            updated_at=now,
        )
        self._session.add(credential)
        await self._session.commit()
        await self._session.refresh(credential)
        return credential

    async def update_password(self, user_id: str, new_hash: str) -> None:
        await self._session.execute(
            update(UserCredential)
            .where(UserCredential.user_id == user_id)
            .values(password_hash=new_hash, updated_at=datetime.now(timezone.utc))
        )
        await self._session.commit()

    async def update_status(self, user_id: str, status: str) -> None:
        await self._session.execute(
            update(UserCredential)
            .where(UserCredential.user_id == user_id)
            .values(account_status=status, updated_at=datetime.now(timezone.utc))
        )
        await self._session.commit()
