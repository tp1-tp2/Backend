from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WordConfidenceSchema(BaseModel):
    word: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    start_time: float
    end_time: float
    sequence_number: int = 0


class TranscribeRequest(BaseModel):
    """Received from Audio Processor via POST /internal/asr/transcribe."""
    audio_path: str
    user_id: str
    audio_id: str
    audio_filename: str
    audio_duration: float


class TranscribeResponse(BaseModel):
    transcription_id: str
    text: str
    confidence_scores: list[WordConfidenceSchema] = []
    processing_time: float


# ---------- WebSocket streaming messages ----------

class AudioChunkMessage(BaseModel):
    """Client → Server."""
    type: str = "audio"
    data: str  # base64-encoded PCM 16kHz 16-bit mono chunk (100ms)


class PartialResultMessage(BaseModel):
    """Server → Client (every 3 seconds)."""
    type: str = "partial"
    text: str
    timestamp: datetime


class FinalResultMessage(BaseModel):
    """Server → Client (on connection close)."""
    type: str = "final"
    transcription_id: str
    text: str
    confidence_scores: list[WordConfidenceSchema] = []
    timestamp: datetime


class ErrorMessage(BaseModel):
    """Server → Client (on error)."""
    type: str = "error"
    error_code: str
    message: str
    timestamp: datetime


# ---------- Streaming session (in-memory state) ----------

class AudioChunk(BaseModel):
    data: bytes
    sequence_number: int
    received_at: datetime


class StreamingSession(BaseModel):
    session_id: str
    user_id: str
    started_at: datetime
    last_activity_at: datetime
    audio_buffer: list[AudioChunk] = []
    partial_transcriptions: list[PartialResultMessage] = []
