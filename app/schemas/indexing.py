"""Indexing API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CourseDocumentPayload(BaseModel):
    course_id: str
    group_id: str | None = None
    title: str
    aliases: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    transliterations: list[str] = Field(default_factory=list)
    description: str
    tags: list[str] = Field(default_factory=list)
    instructor: str
    language: str
    available_languages: list[str] = Field(default_factory=list)
    category: str
    topic: str
    competency_name: str | None = None
    levels: list[str] = Field(default_factory=list)
    updated_on: str | None = None
    difficulty: str | None = None
    duration_minutes: int | None = None
    certification: bool | None = None
    popularity_score: float = 0.0
    recency_score: float = 0.0
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class BulkIndexRequest(BaseModel):
    documents: list[CourseDocumentPayload]
    idempotency_key: str | None = None


class UpdateIndexRequest(BaseModel):
    document: CourseDocumentPayload
    idempotency_key: str | None = None


class DeleteIndexRequest(BaseModel):
    course_ids: list[str]
    idempotency_key: str | None = None


class ReindexRequest(BaseModel):
    reload_sample_data: bool = False
    documents: list[CourseDocumentPayload] = Field(default_factory=list)


class IndexingResponse(BaseModel):
    schema_version: str
    indexed_count: int = 0
    deleted_count: int = 0
    total_documents: int = 0
    detail: str
