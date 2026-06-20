from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.transcription import Transcription, WordConfidence


class TranscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, transcription_id: str) -> Transcription | None:
        result = await self._session.execute(
            select(Transcription)
            .where(Transcription.transcription_id == transcription_id)
            .options(selectinload(Transcription.word_confidences))
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Transcription]:
        result = await self._session.execute(
            select(Transcription)
            .where(Transcription.user_id == user_id)
            .order_by(Transcription.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        result = await self._session.execute(
            select(func.count()).where(Transcription.user_id == user_id)
        )
        return result.scalar_one()

    async def get_latest_date_by_user(self, user_id: str) -> datetime | None:
        result = await self._session.execute(
            select(func.max(Transcription.created_at)).where(
                Transcription.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, transcription: Transcription) -> None:
        await self._session.delete(transcription)
        await self._session.commit()

    async def create(
        self,
        transcription_id: str,
        user_id: str,
        audio_id: str,
        text: str,
        audio_filename: str,
        audio_duration: Decimal,
        processing_time: Decimal,
        word_confidences: list[WordConfidence] | None = None,
    ) -> Transcription:
        entry = Transcription(
            transcription_id=transcription_id,
            user_id=user_id,
            audio_id=audio_id,
            text=text,
            audio_filename=audio_filename,
            audio_duration=audio_duration,
            processing_time=processing_time,
            created_at=datetime.now(timezone.utc),
        )
        if word_confidences:
            entry.word_confidences = word_confidences
        self._session.add(entry)
        await self._session.commit()
        await self._session.refresh(entry)
        return entry
