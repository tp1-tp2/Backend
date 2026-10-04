from fastapi import HTTPException


class UnsupportedFormatError(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"errorCode": "VALIDATION_004", "message": "Unsupported audio format"})


class FileSizeExceededError(HTTPException):
    def __init__(self):
        super().__init__(status_code=413, detail={"errorCode": "VALIDATION_002", "message": "Audio file size exceeds 50MB limit"})


class CorruptedFileError(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"errorCode": "VALIDATION_005", "message": "File cannot be processed"})


class InvalidSampleRateError(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"errorCode": "VALIDATION_006", "message": "Unsupported sample rate"})


class DurationExceededError(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"errorCode": "VALIDATION_007", "message": "Audio duration exceeds maximum limit"})


class AsrUnavailableError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=503,
            detail={"errorCode": "ASR_001", "message": "ASR service unavailable"},
            headers={"Retry-After": "5"},
        )


class AsrTimeoutError(HTTPException):
    def __init__(self):
        super().__init__(status_code=504, detail={"errorCode": "ASR_002", "message": "Transcription timeout"})


class QueueFullError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=429,
            detail={"errorCode": "JOB_002", "message": "Transcription queue is full, retry later"},
            headers={"Retry-After": "10"},
        )


class JobQueueUnavailableError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=503,
            detail={"errorCode": "JOB_003", "message": "Job queue unavailable"},
            headers={"Retry-After": "5"},
        )
