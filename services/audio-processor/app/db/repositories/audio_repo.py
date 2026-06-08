from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audio import AudioFile


class AudioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, audio_id: str) -> AudioFile | None:
        result = await self._session.execute(
            select(AudioFile).where(AudioFile.audio_id == audio_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: str) -> list[AudioFile]:
        result = await self._session.execute(
            select(AudioFile)
            .where(AudioFile.user_id == user_id)
            .order_by(AudioFile.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        audio_id: str,
        user_id: str,
        filename: str,
        original_format: str,
        file_size_bytes: int,
        duration_seconds: Decimal,
        sample_rate: int,
        channels: int,
        bit_rate: int,
        storage_path: str,
    ) -> AudioFile:
        entry = AudioFile(
            audio_id=audio_id,
            user_id=user_id,
            filename=filename,
            original_format=original_format,
            file_size_bytes=file_size_bytes,
            duration_seconds=duration_seconds,
            sample_rate=sample_rate,
            channels=channels,
            bit_rate=bit_rate,
            storage_path=storage_path,
            uploaded_at=datetime.now(timezone.utc),
        )
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry

    async def mark_processed(self, audio_id: str, processed_path: str) -> None:
        await self._session.execute(
            update(AudioFile)
            .where(AudioFile.audio_id == audio_id)
            .values(
                processed_path=processed_path,
                processed_at=datetime.now(timezone.utc),
            )
        )
        await self._session.commit()
