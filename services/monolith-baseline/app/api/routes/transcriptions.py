import math

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.transcription import Transcription
from app.schemas.transcription import (
    PaginationMeta,
    TranscriptionListItem,
    TranscriptionListResponse,
    TranscriptionResponse,
    WordConfidenceSchema,
)
from app.services import pipeline_service

router = APIRouter(prefix="/api/v1", tags=["transcriptions"])


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return await pipeline_service.process_upload(session, file, user["user_id"])


@router.get("/transcriptions", response_model=TranscriptionListResponse)
async def list_transcriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    base = select(Transcription).where(Transcription.user_id == user["user_id"])
    total_items = await session.scalar(select(func.count()).select_from(base.subquery()))
    total_items = total_items or 0

    rows = (
        await session.execute(
            base.order_by(Transcription.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return TranscriptionListResponse(
        transcriptions=[TranscriptionListItem.model_validate(t) for t in rows],
        pagination=PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_pages=max(1, math.ceil(total_items / page_size)),
            total_items=total_items,
        ),
    )


@router.get("/transcriptions/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(
    transcription_id: str,
    session: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    t = await session.scalar(
        select(Transcription)
        .options(selectinload(Transcription.word_confidences))
        .where(
            Transcription.transcription_id == transcription_id,
            Transcription.user_id == user["user_id"],
        )
    )
    if not t:
        raise HTTPException(status_code=404, detail={"errorCode": "TRANS_001", "message": "Transcription not found"})

    return TranscriptionResponse(
        transcription_id=t.transcription_id,
        user_id=t.user_id,
        audio_id=t.audio_id,
        text=t.text,
        audio_filename=t.audio_filename,
        audio_duration=float(t.audio_duration),
        processing_time=float(t.processing_time),
        created_at=t.created_at,
        confidence_scores=[WordConfidenceSchema.model_validate(w) for w in t.word_confidences],
        device_used=t.device_used,
        compute_type=t.compute_type,
    )
