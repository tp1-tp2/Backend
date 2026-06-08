from fastapi import HTTPException


class AuthenticationError(HTTPException):
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(status_code=401, detail={"errorCode": "AUTH_001", "message": message})


class AuthorizationError(HTTPException):
    def __init__(self, message: str = "Access denied to this resource"):
        super().__init__(status_code=403, detail={"errorCode": "AUTH_002", "message": message})


class ServiceUnavailableError(HTTPException):
    def __init__(self, service: str):
        super().__init__(
            status_code=502,
            detail={"errorCode": "SYSTEM_002", "message": f"{service} temporarily unavailable"},
        )


class GatewayTimeoutError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=504,
            detail={"errorCode": "SYSTEM_004", "message": "Request processing timeout after 30 seconds"},
        )
