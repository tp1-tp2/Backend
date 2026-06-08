from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import TokenBlocklist


class BlocklistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token_hash: str, user_id: str, expires_at: datetime) -> None:
        entry = TokenBlocklist(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
            blocked_at=datetime.now(timezone.utc),
        )
        self._session.add(entry)
        await self._session.commit()

    async def exists(self, token_hash: str) -> bool:
        result = await self._session.execute(
            select(TokenBlocklist).where(TokenBlocklist.token_hash == token_hash)
        )
        return result.scalar_one_or_none() is not None

    async def add_all_for_user(self, user_id: str, expires_at: datetime, token_hashes: list[str]) -> None:
        """Invalidate multiple tokens at once (used on password reset)."""
        now = datetime.now(timezone.utc)
        for token_hash in token_hashes:
            entry = TokenBlocklist(
                token_hash=token_hash,
                user_id=user_id,
                expires_at=expires_at,
                blocked_at=now,
            )
            self._session.add(entry)
        await self._session.commit()

    async def delete_expired(self) -> int:
        """Remove expired entries. Returns count deleted."""
        result = await self._session.execute(
            delete(TokenBlocklist).where(
                TokenBlocklist.expires_at < datetime.now(timezone.utc)
            )
        )
        await self._session.commit()
        return result.rowcount
