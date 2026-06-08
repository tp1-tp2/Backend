from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserProfile


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: str) -> UserProfile | None:
        result = await self._session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> UserProfile | None:
        result = await self._session.execute(
            select(UserProfile).where(UserProfile.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: str, email: str, full_name: str) -> UserProfile:
        now = datetime.now(timezone.utc)
        user = UserProfile(
            user_id=user_id,
            email=email,
            full_name=full_name,
            created_at=now,
            updated_at=now,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def update(self, user_id: str, **fields) -> UserProfile | None:
        fields["updated_at"] = datetime.now(timezone.utc)
        await self._session.execute(
            update(UserProfile)
            .where(UserProfile.user_id == user_id)
            .values(**fields)
        )
        await self._session.commit()
        return await self.get_by_id(user_id)
