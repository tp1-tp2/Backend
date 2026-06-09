from fastapi import APIRouter

from app.schemas.transcription import TranscribeRequest, TranscribeResponse
from app.services import whisper_service

router = APIRouter(prefix="/internal/asr", tags=["internal"])


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(body: TranscribeRequest):
    return await whisper_service.transcribe(
        audio_path=body.audio_path,
        user_id=body.user_id,
        audio_id=body.audio_id,
        audio_filename=body.audio_filename,
        audio_duration=body.audio_duration,
    )
