"""Request guards for auth, rate limiting, and request sizing."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


def _error_response(status_code: int, code: str, message: str, details: dict[str, object] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "schema_version": settings.schema_version,
            "request_id": str(uuid.uuid4()),
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
        },
    )


class RequestGuardMiddleware(BaseHTTPMiddleware):
    """Applies API key auth, lightweight rate limiting, and upload/request size checks."""

    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._exempt_prefixes = {
            "/",
            "/demo",
            "/docs",
            "/redoc",
            "/openapi.json",
            f"{settings.api_prefix}/health",
            f"{settings.api_prefix}/ready",
            f"{settings.api_prefix}/live",
        }

    def _is_exempt(self, path: str) -> bool:
        return any(path == prefix or path.startswith(f"{prefix}/") for prefix in self._exempt_prefixes if prefix != "/") or path == "/"

    def _client_identity(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        api_key = request.headers.get(settings.api_key_header_name)
        if api_key:
            return f"key:{api_key}"
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    def _authorize(self, request: Request) -> JSONResponse | None:
        if not settings.auth_enabled or self._is_exempt(request.url.path):
            return None
        supplied = request.headers.get(settings.api_key_header_name)
        if not supplied:
            return _error_response(
                401,
                "auth_required",
                "Missing API key",
                {"header": settings.api_key_header_name},
            )
        if supplied not in settings.api_keys:
            return _error_response(403, "auth_invalid", "Invalid API key", {"header": settings.api_key_header_name})
        return None

    def _apply_rate_limit(self, request: Request) -> JSONResponse | None:
        if not settings.rate_limit_enabled or self._is_exempt(request.url.path):
            return None
        identity = f"{self._client_identity(request)}:{request.url.path}"
        now = time.time()
        window_start = now - settings.rate_limit_window_seconds
        with self._lock:
            bucket = self._hits[identity]
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            if len(bucket) >= settings.rate_limit_requests:
                retry_after = max(1, int(bucket[0] + settings.rate_limit_window_seconds - now))
                response = _error_response(
                    429,
                    "rate_limit_exceeded",
                    "Rate limit exceeded",
                    {
                        "route": request.url.path,
                        "window_seconds": settings.rate_limit_window_seconds,
                        "limit": settings.rate_limit_requests,
                        "retry_after_seconds": retry_after,
                    },
                )
                response.headers["Retry-After"] = str(retry_after)
                return response
            bucket.append(now)
        return None

    def _check_size(self, request: Request) -> JSONResponse | None:
        header = request.headers.get("content-length")
        if header is None:
            return None
        try:
            content_length = int(header)
        except ValueError:
            return None
        limit = settings.max_audio_upload_bytes if request.url.path.endswith("/search/voice") else settings.max_request_bytes
        if content_length > limit:
            return _error_response(
                413,
                "request_too_large",
                "Request body exceeds configured size limit",
                {"content_length": content_length, "max_allowed_bytes": limit},
            )
        return None

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        for checker in (self._check_size, self._authorize, self._apply_rate_limit):
            response = checker(request)
            if response is not None:
                return response
        return await call_next(request)
