from fastapi import HTTPException


class TranscriptionNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail={"errorCode": "RESOURCE_001", "message": "Transcription not found"})


class AccessDeniedError(HTTPException):
    def __init__(self):
        super().__init__(status_code=403, detail={"errorCode": "AUTH_002", "message": "Access denied"})


class InvalidPageSizeError(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"errorCode": "VALIDATION_001", "message": "Page size must be between 1 and 100"})


class UnsupportedFormatError(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"errorCode": "VALIDATION_004", "message": "Unsupported format"})
