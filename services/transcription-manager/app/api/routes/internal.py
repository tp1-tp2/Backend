from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.schemas.transcription import (
    CreateTranscriptionRequest,
    TranscriptionResponse,
    TranscriptionSummary,
)
from app.services.transcription_service import TranscriptionService

router = APIRouter(prefix="/internal/transcriptions", tags=["internal"])


def _svc(session: AsyncSession = Depends(get_session)) -> TranscriptionService:
    return TranscriptionService(session)


@router.post("", response_model=TranscriptionResponse, status_code=201)
async def create_transcription(
    body: CreateTranscriptionRequest,
    svc: TranscriptionService = Depends(_svc),
):
    return await svc.create(body)


@router.get("/summary", response_model=TranscriptionSummary)
async def get_summary(
    x_user_id: str = Header(..., alias="X-User-Id"),
    svc: TranscriptionService = Depends(_svc),
):
    return await svc.get_summary(x_user_id)
