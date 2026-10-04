import httpx
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_http_client, get_session
from app.schemas.audio import AudioUploadResponse, JobAcceptedResponse
from app.services.audio_service import AudioService

router = APIRouter(prefix="/internal/audio", tags=["internal"])


def _svc(
    session: AsyncSession = Depends(get_session),
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> AudioService:
    return AudioService(session, http_client)


@router.post("/process", response_model=AudioUploadResponse)
async def process_audio(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    svc: AudioService = Depends(_svc),
):
    return await svc.process_upload(file, user_id)


@router.post("/jobs", response_model=JobAcceptedResponse, status_code=202)
async def submit_job(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    svc: AudioService = Depends(_svc),
):
    return await svc.submit_job(file, user_id)
