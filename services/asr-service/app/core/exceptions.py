from fastapi import HTTPException

from app.core.config import settings


class ModelUnavailableError(HTTPException):
    def __init__(self):
        super().__init__(status_code=503, detail={"errorCode": "ASR_001", "message": "ASR service unavailable"})


class TranscriptionTimeoutError(HTTPException):
    def __init__(self):
        super().__init__(status_code=504, detail={"errorCode": "ASR_002", "message": "Transcription timeout"})


class CapacityReachedError(HTTPException):
    def __init__(self, message: str = "Service capacity limit reached"):
        super().__init__(
            status_code=503,
            detail={"errorCode": "ASR_003", "message": message},
            headers={"Retry-After": str(settings.retry_after_seconds)},
        )
