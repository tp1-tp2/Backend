from fastapi import HTTPException


class EmailAlreadyExistsError(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"errorCode": "VALIDATION_003", "message": "Email already registered"})


class ValidationError(HTTPException):
    def __init__(self, field: str, rule: str):
        super().__init__(
            status_code=400,
            detail={"errorCode": "VALIDATION_001", "message": f"Validation failed", "field": field, "rule": rule},
        )


class UserNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail={"errorCode": "RESOURCE_001", "message": "User not found"})
