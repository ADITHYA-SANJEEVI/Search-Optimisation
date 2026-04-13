"""Voice search schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.search import SearchResponse


class VoiceSearchResponse(BaseModel):
    schema_version: str
    transcript: str | None = None
    transcript_cleaned: str | None = None
    transcription_confidence: float | None = None
    degraded: bool = False
    degradation_reason: str | None = None
    search_response: SearchResponse | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
