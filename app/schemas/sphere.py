"""Typed results for the Sphere compatibility adapters."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.indexing import CourseDocumentPayload
from app.schemas.search import SearchRequest


class SphereAdapterDiagnostic(BaseModel):
    severity: Literal["warning", "error"]
    code: str
    message: str
    record_index: int | None = None
    identifier: str | None = None
    field: str | None = None


class SphereCatalogueConversion(BaseModel):
    documents: list[CourseDocumentPayload] = Field(default_factory=list)
    diagnostics: list[SphereAdapterDiagnostic] = Field(default_factory=list)
    source_count: int | None = None
    source_content_length: int = 0
    facets_present: bool = False


class SphereRequestTranslation(BaseModel):
    search_request: SearchRequest
    source_query_fields: dict[str, str | None]
    source_filters: dict[str, list[str]] = Field(default_factory=dict)
    source_sort: list[dict[str, Any]] = Field(default_factory=list)
