from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcription import WordConfidence


class WordConfidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_bulk(
        self,
        transcription_id: str,
        words: list[dict],
    ) -> list[WordConfidence]:
        """Insert multiple word confidence records for a transcription.

        Each dict must have: word, confidence, start_time, end_time, sequence_number.
        """
        entries = [
            WordConfidence(
                transcription_id=transcription_id,
                word=w["word"],
                confidence=Decimal(str(w["confidence"])),
                start_time=Decimal(str(w["start_time"])),
                end_time=Decimal(str(w["end_time"])),
                sequence_number=w["sequence_number"],
            )
            for w in words
        ]
        self._session.add_all(entries)
        await self._session.commit()
        return entries

    async def get_by_transcription(self, transcription_id: str) -> list[WordConfidence]:
        result = await self._session.execute(
            select(WordConfidence)
            .where(WordConfidence.transcription_id == transcription_id)
            .order_by(WordConfidence.sequence_number)
        )
        return list(result.scalars().all())

    async def delete_by_transcription(self, transcription_id: str) -> None:
        await self._session.execute(
            delete(WordConfidence).where(
                WordConfidence.transcription_id == transcription_id
            )
        )
        await self._session.commit()
