"""Custom errors and API handlers."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings


class ServiceError(Exception):
    """Base application error with a transport-safe payload."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
        details = exc.details if not settings.safe_error_mode or exc.status_code < 500 else {}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "schema_version": settings.schema_version,
                "request_id": str(uuid.uuid4()),
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": details,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        details = {"exception_type": exc.__class__.__name__} if not settings.safe_error_mode else {}
        return JSONResponse(
            status_code=500,
            content={
                "schema_version": settings.schema_version,
                "request_id": str(uuid.uuid4()),
                "error": {
                    "code": "internal_error",
                    "message": "Unexpected server error",
                    "details": details,
                },
            },
        )
