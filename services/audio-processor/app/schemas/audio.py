from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AudioMetadata(BaseModel):
    format: str
    duration: float = Field(..., ge=0.0, le=3600.0)
    sample_rate: int = Field(..., ge=8000, le=48000, alias="sampleRate")
    bit_rate: int = Field(..., alias="bitRate")
    channels: int = Field(..., ge=1, le=2)
    codec: Optional[str] = None

    model_config = {"populate_by_name": True}


class AudioUploadResponse(BaseModel):
    audio_id: str
    processed_path: str
    metadata: AudioMetadata
    transcription_id: str | None = None
    transcription_text: str | None = None

    model_config = {"populate_by_name": True}


# ---------- Internal (service-to-service) ----------

class ProcessAudioRequest(BaseModel):
    user_id: str


class TranscribeForwardRequest(BaseModel):
    audio_path: str
    user_id: str
    audio_id: str
    audio_filename: str
    audio_duration: float
