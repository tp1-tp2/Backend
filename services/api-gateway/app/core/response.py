from datetime import datetime, timezone

from fastapi.responses import JSONResponse


def success_response(data: dict, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "success",
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def error_response(error_code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "errorCode": error_code,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
