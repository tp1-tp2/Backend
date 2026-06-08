from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import PasswordRecoveryToken


class RecoveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, token: str, user_id: str, email: str, expires_at: datetime
    ) -> PasswordRecoveryToken:
        entry = PasswordRecoveryToken(
            token=token,
            user_id=user_id,
            email=email,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            used=False,
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def get_valid(self, token: str) -> PasswordRecoveryToken | None:
        """Return token only if it exists, is not used, and has not expired."""
        result = await self._session.execute(
            select(PasswordRecoveryToken).where(
                PasswordRecoveryToken.token == token,
                PasswordRecoveryToken.used == False,  # noqa: E712
                PasswordRecoveryToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: str) -> None:
        await self._session.execute(
            update(PasswordRecoveryToken)
            .where(PasswordRecoveryToken.token == token)
            .values(used=True)
        )
        await self._session.commit()
