from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WordConfidenceSchema(BaseModel):
    word: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    start_time: float
    end_time: float
    sequence_number: int = 0

    model_config = {"from_attributes": True}


class TranscriptionResponse(BaseModel):
    transcription_id: str
    user_id: str
    audio_id: str
    text: str
    audio_filename: str
    audio_duration: float
    processing_time: float
    created_at: datetime
    confidence_scores: list[WordConfidenceSchema] = []

    model_config = {"from_attributes": True}


class TranscriptionListItem(BaseModel):
    transcription_id: str
    text: str
    audio_filename: str
    audio_duration: float
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginationMeta(BaseModel):
    current_page: int
    page_size: int
    total_pages: int
    total_items: int


class TranscriptionListResponse(BaseModel):
    transcriptions: list[TranscriptionListItem]
    pagination: PaginationMeta


class RenameTranscriptionRequest(BaseModel):
    audio_filename: str = Field(..., min_length=1, max_length=255)


# ---------- Internal (service-to-service) ----------

class CreateTranscriptionRequest(BaseModel):
    transcription_id: str
    user_id: str
    audio_id: str
    text: str
    audio_filename: str
    audio_duration: float
    processing_time: float
    confidence_scores: list[WordConfidenceSchema] = []


class TranscriptionSummary(BaseModel):
    total: int
    latest_at: Optional[datetime] = None
