"""Health API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    name: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    schema_version: str
    status: str
    service: str
    dependencies: list[DependencyStatus]
