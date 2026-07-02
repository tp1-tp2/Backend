import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.transcription import TranscribeResponse
from app.services import whisper_service

router = APIRouter(prefix="/internal/asr", tags=["internal"])


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    audio_id: str = Form(...),
    audio_filename: str = Form(...),
    audio_duration: float = Form(...),
):
    content = await file.read()
    out_dir = Path(tempfile.gettempdir()) / "asr_audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_path = str(out_dir / f"{audio_id}.wav")
    Path(audio_path).write_bytes(content)
    try:
        return await whisper_service.transcribe(
            audio_path=audio_path,
            user_id=user_id,
            audio_id=audio_id,
            audio_filename=audio_filename,
            audio_duration=audio_duration,
        )
    finally:
        Path(audio_path).unlink(missing_ok=True)
