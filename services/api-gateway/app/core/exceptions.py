from fastapi import HTTPException

from app.core.config import settings


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


class UpstreamOverloadedError(HTTPException):
    """503 + Retry-After: a dependency answered but could not serve the request
    (overloaded / degraded). Distinct from 401 so clients and load tests can
    tell "bad credentials" apart from "try again shortly".
    """

    def __init__(self, service: str):
        super().__init__(
            status_code=503,
            detail={"errorCode": "SYSTEM_003", "message": f"{service} overloaded, retry later"},
            headers={"Retry-After": str(settings.retry_after_seconds)},
        )


class GatewayTimeoutError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=504,
            detail={"errorCode": "SYSTEM_004", "message": "Upstream request timed out"},
        )
