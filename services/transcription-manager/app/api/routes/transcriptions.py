from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.schemas.transcription import (
    RenameTranscriptionRequest,
    TranscriptionListResponse,
    TranscriptionResponse,
)
from app.services.download_service import DownloadService
from app.services.transcription_service import TranscriptionService

router = APIRouter(prefix="/api/v1/transcriptions", tags=["transcriptions"])


def _svc(session: AsyncSession = Depends(get_session)) -> TranscriptionService:
    return TranscriptionService(session)


def _dl(session: AsyncSession = Depends(get_session)) -> DownloadService:
    return DownloadService(session)


@router.get("", response_model=TranscriptionListResponse)
async def list_transcriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    x_user_id: str = Header(..., alias="X-User-Id"),
    svc: TranscriptionService = Depends(_svc),
):
    return await svc.list_by_user(x_user_id, page=page, page_size=page_size)


@router.get("/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(
    transcription_id: str,
    x_user_id: str = Header(..., alias="X-User-Id"),
    svc: TranscriptionService = Depends(_svc),
):
    return await svc.get_by_id(transcription_id, x_user_id)


@router.patch("/{transcription_id}", response_model=TranscriptionResponse)
async def rename_transcription(
    transcription_id: str,
    body: RenameTranscriptionRequest,
    x_user_id: str = Header(..., alias="X-User-Id"),
    svc: TranscriptionService = Depends(_svc),
):
    return await svc.rename_by_id(transcription_id, x_user_id, body.audio_filename)


@router.delete("/{transcription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcription(
    transcription_id: str,
    x_user_id: str = Header(..., alias="X-User-Id"),
    svc: TranscriptionService = Depends(_svc),
):
    await svc.delete_by_id(transcription_id, x_user_id)


@router.get("/{transcription_id}/download")
async def download_transcription(
    transcription_id: str,
    format: str = Query(..., description="txt, json, or srt"),
    x_user_id: str = Header(..., alias="X-User-Id"),
    dl: DownloadService = Depends(_dl),
):
    content, media_type, filename = await dl.get_file(transcription_id, x_user_id, format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
