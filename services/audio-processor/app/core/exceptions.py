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
