"""Custom application exceptions with the error shape defined in docs/api.md."""
from datetime import datetime, timezone
from fastapi import Request
from fastapi.responses import JSONResponse


class EcoLoopException(Exception):
    def __init__(self, code: str, message: str, errors: list[str] | None = None, status_code: int = 400):
        self.code = code
        self.message = message
        self.errors = errors or []
        self.status_code = status_code


async def ecoloop_exception_handler(request: Request, exc: EcoLoopException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": {
                "code": exc.code,
                "message": exc.message,
                "errors": exc.errors,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
