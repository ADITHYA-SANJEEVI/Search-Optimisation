"""Shared API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 10
    total_results: int = 0
    total_pages: int = 0
    next_cursor: str | None = None


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class HighlightFields(BaseModel):
    title: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class SuggestionItem(BaseModel):
    text: str
    type: str
    confidence: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SuggestionGroup(BaseModel):
    section: str
    items: list[SuggestionItem]
