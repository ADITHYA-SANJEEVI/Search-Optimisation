"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_container
from app.core.config import settings
from app.schemas.health import DependencyStatus, HealthResponse
from app.services.bootstrap import ServiceContainer

router = APIRouter(tags=["health"])


def _response(container: ServiceContainer, status: str) -> HealthResponse:
    backend_details = {"document_count": container.backend.document_count()}
    backend_status = "up"
    if hasattr(container.backend, "health_details"):
        live_details = container.backend.health_details()
        backend_status = "up" if live_details.get("status") not in {"down", "degraded"} else live_details["status"]
        backend_details.update(live_details)
    dependencies = [
        DependencyStatus(
            name="search_backend",
            status=backend_status,
            details=backend_details,
        ),
        DependencyStatus(
            name="semantic_encoder",
            status="up" if container.encoder.available else "degraded",
            details={
                "model_loaded": container.encoder._model is not None,
                "provider": container.encoder.provider,
            },
        ),
        *[DependencyStatus(**item) for item in container.analytics.dependencies_status()],
    ]
    return HealthResponse(
        schema_version=settings.schema_version,
        status=status,
        service=settings.app_name,
        dependencies=dependencies,
    )


@router.get("/health", response_model=HealthResponse)
def health(container: ServiceContainer = Depends(get_container)) -> HealthResponse:
    response = _response(container, "healthy")
    if response.dependencies[0].status != "up":
        response.status = "degraded"
    return response


@router.get("/ready", response_model=HealthResponse)
def ready(container: ServiceContainer = Depends(get_container)) -> HealthResponse:
    status = "ready" if container.backend.document_count() > 0 else "warming"
    response = _response(container, status)
    if response.dependencies[0].status != "up":
        response.status = "unavailable"
    if response.status != "ready":
        return JSONResponse(status_code=503, content=response.model_dump())
    return response


@router.get("/live", response_model=HealthResponse)
def live(container: ServiceContainer = Depends(get_container)) -> HealthResponse:
    return HealthResponse(schema_version=settings.schema_version, status="live", service=settings.app_name,
                          dependencies=[])
