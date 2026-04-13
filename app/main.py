"""FastAPI application entrypoint."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.health import router as health_router
from app.api.index import router as index_router
from app.api.search import router as search_router
from app.core.config import settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging
from app.core.security import RequestGuardMiddleware
from app.services.bootstrap import build_container

configure_logging()
app = FastAPI(title=settings.app_name, version=settings.schema_version)
app.add_middleware(RequestGuardMiddleware)
install_exception_handlers(app)
app.state.container = build_container()
static_dir = Path(__file__).resolve().parent / "static"

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(index_router, prefix=settings.api_prefix)
app.include_router(search_router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "version": settings.schema_version}


@app.get("/demo", include_in_schema=False)
def demo() -> FileResponse:
    return FileResponse(static_dir / "demo.html")


@app.get("/demo/debug", include_in_schema=False)
def debug_demo() -> FileResponse:
    return FileResponse(static_dir / "debug.html")
