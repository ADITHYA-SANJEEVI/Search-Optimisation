"""Search API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import HighlightFields, Pagination, SuggestionGroup


class SearchFilters(BaseModel):
    language: str | None = None
    category: str | None = None
    topic: str | None = None
    instructor: str | None = None
    difficulty: str | None = None
    duration_max: int | None = None
    certification: bool | None = None


class SearchRequest(BaseModel):
    query: str
    filters: SearchFilters = Field(default_factory=SearchFilters)
    page: int = 1
    page_size: int = 10
    cursor: str | None = None
    sort: Literal["relevance", "popularity", "newest", "alphabetical", "recommended"] = "relevance"
    preferred_language: str | None = None
    debug: bool = False
    explain: bool = True
    experiment_tag: str | None = None
    low_latency: bool = False


class SearchIntentPayload(BaseModel):
    intent_type: str
    topics: list[str] = Field(default_factory=list)
    specialties: list[str] = Field(default_factory=list)
    language_preferences: list[str] = Field(default_factory=list)
    difficulty: str | None = None
    educational_goal: str | None = None
    summary: str | None = None


class CourseVariant(BaseModel):
    course_id: str
    title: str
    language: str


class SearchResultItem(BaseModel):
    course_id: str
    group_id: str
    title: str
    description: str
    instructor: str
    language: str
    available_languages: list[str]
    category: str
    topic: str
    difficulty: str | None = None
    duration_minutes: int | None = None
    certification: bool | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float
    confidence: float
    matched_terms: list[str] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    highlights: HighlightFields
    grouped_variants: list[CourseVariant] = Field(default_factory=list)
    debug: dict[str, Any] = Field(default_factory=dict)


class NoResultsGuidance(BaseModel):
    message: str
    suggestions: list[str] = Field(default_factory=list)
    filters_to_relax: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    schema_version: str
    original_query: str
    normalized_query: str
    corrected_query: str | None = None
    did_you_mean: str | None = None
    search_instead_for: str | None = None
    detected_languages: list[str] = Field(default_factory=list)
    extracted_search_intent: SearchIntentPayload
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    results: list[SearchResultItem] = Field(default_factory=list)
    grouped_suggestions: list[SuggestionGroup] = Field(default_factory=list)
    alternate_queries: list[str] = Field(default_factory=list)
    no_results_guidance: NoResultsGuidance | None = None
    facets: dict[str, dict[str, int]] = Field(default_factory=dict)
    pagination: Pagination
    debug_info: dict[str, Any] | None = None
