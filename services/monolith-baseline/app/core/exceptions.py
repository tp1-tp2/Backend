"""Merged from auth-service, audio-processor and asr-service's exceptions.py —
same error codes/status codes as the real stack, so E3's HTTP-level comparison
(error rate, status codes) is meaningful across both architectures.
"""
from fastapi import HTTPException


class InvalidCredentialsError(HTTPException):
    def __init__(self):
        super().__init__(status_code=401, detail={"errorCode": "AUTH_001", "message": "Invalid credentials"})


class AccountLockedError(HTTPException):
    def __init__(self):
        super().__init__(status_code=403, detail={"errorCode": "AUTH_003", "message": "Account is locked or disabled"})


class TokenInvalidError(HTTPException):
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(status_code=401, detail={"errorCode": "AUTH_001", "message": message})


class EmailAlreadyExistsError(HTTPException):
    def __init__(self):
        super().__init__(status_code=409, detail={"errorCode": "USER_001", "message": "Email already registered"})


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


class ModelUnavailableError(HTTPException):
    def __init__(self):
        super().__init__(status_code=503, detail={"errorCode": "ASR_001", "message": "ASR service unavailable"})


class TranscriptionTimeoutError(HTTPException):
    def __init__(self):
        super().__init__(status_code=504, detail={"errorCode": "ASR_002", "message": "Transcription timeout"})
