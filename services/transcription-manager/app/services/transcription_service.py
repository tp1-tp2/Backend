import math
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AccessDeniedError, InvalidPageSizeError, TranscriptionNotFoundError
from app.db.repositories import TranscriptionRepository, WordConfidenceRepository
from app.models.transcription import Transcription
from app.schemas.transcription import (
    CreateTranscriptionRequest,
    PaginationMeta,
    TranscriptionListItem,
    TranscriptionListResponse,
    TranscriptionResponse,
    TranscriptionSummary,
    WordConfidenceSchema,
)


def _to_response(t: Transcription) -> TranscriptionResponse:
    return TranscriptionResponse(
        transcription_id=t.transcription_id,
        user_id=t.user_id,
        audio_id=t.audio_id,
        text=t.text,
        audio_filename=t.audio_filename,
        audio_duration=float(t.audio_duration),
        processing_time=float(t.processing_time),
        created_at=t.created_at,
        confidence_scores=[
            WordConfidenceSchema.model_validate(w) for w in (t.word_confidences or [])
        ],
        device_used=t.device_used,
        compute_type=t.compute_type,
    )


class TranscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self._trans = TranscriptionRepository(session)
        self._words = WordConfidenceRepository(session)

    async def create(self, req: CreateTranscriptionRequest) -> TranscriptionResponse:
        from decimal import Decimal

        transcription = await self._trans.create(
            transcription_id=req.transcription_id,
            user_id=req.user_id,
            audio_id=req.audio_id,
            text=req.text,
            audio_filename=req.audio_filename,
            audio_duration=Decimal(str(req.audio_duration)),
            processing_time=Decimal(str(req.processing_time)),
            device_used=req.device_used,
            compute_type=req.compute_type,
        )

        if req.confidence_scores:
            await self._words.create_bulk(
                req.transcription_id,
                [w.model_dump() for w in req.confidence_scores],
            )

        # Reload with word_confidences
        transcription = await self._trans.get_by_id(req.transcription_id)
        return _to_response(transcription)

    async def get_by_id(
        self, transcription_id: str, user_id: str
    ) -> TranscriptionResponse:
        t = await self._trans.get_by_id(transcription_id)
        if not t:
            raise TranscriptionNotFoundError()
        if t.user_id != user_id:
            raise AccessDeniedError()
        return _to_response(t)

    async def list_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> TranscriptionListResponse:
        if not (1 <= page_size <= settings.max_page_size):
            raise InvalidPageSizeError()

        offset = (page - 1) * page_size
        items = await self._trans.get_by_user(user_id, limit=page_size, offset=offset)
        total = await self._trans.count_by_user(user_id)
        total_pages = max(1, math.ceil(total / page_size))

        return TranscriptionListResponse(
            transcriptions=[TranscriptionListItem.model_validate(t) for t in items],
            pagination=PaginationMeta(
                current_page=page,
                page_size=page_size,
                total_pages=total_pages,
                total_items=total,
            ),
        )

    async def delete_by_id(self, transcription_id: str, user_id: str) -> None:
        t = await self._trans.get_by_id(transcription_id)
        if not t:
            raise TranscriptionNotFoundError()
        if t.user_id != user_id:
            raise AccessDeniedError()
        await self._trans.delete(t)

    async def rename_by_id(
        self, transcription_id: str, user_id: str, audio_filename: str
    ) -> TranscriptionResponse:
        t = await self._trans.get_by_id(transcription_id)
        if not t:
            raise TranscriptionNotFoundError()
        if t.user_id != user_id:
            raise AccessDeniedError()
        t = await self._trans.rename(t, audio_filename)
        return _to_response(t)

    async def get_summary(self, user_id: str) -> TranscriptionSummary:
        total = await self._trans.count_by_user(user_id)
        latest_at = await self._trans.get_latest_date_by_user(user_id)
        return TranscriptionSummary(total=total, latest_at=latest_at)
