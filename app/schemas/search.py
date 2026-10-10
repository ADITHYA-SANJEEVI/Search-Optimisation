"""Search API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict, AliasChoices

from app.schemas.common import HighlightFields, Pagination, SuggestionGroup


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str | None = None
    category: str | None = None
    categories: list[str] = Field(default_factory=list)
    content_types: list[str] = Field(default_factory=list)
    publication_statuses: list[str] = Field(default_factory=list)
    topic: str | None = None
    instructor: str | None = None
    difficulty: str | None = None
    duration_max: int | None = None
    certification: bool | None = None


class AdvancedSearchFilters(SearchFilters):
    model_config = ConfigDict(extra="forbid", strict=True)
    categories: list[str] = Field(default_factory=list, validation_alias=AliasChoices("primaryCategory", "categories"))
    content_types: list[str] = Field(default_factory=list, validation_alias=AliasChoices("contentType", "content_types"))
    publication_statuses: list[str] = Field(default_factory=list, validation_alias=AliasChoices("status", "publication_statuses"))


class AdvancedSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: str = Field(default="", max_length=240)
    filters: AdvancedSearchFilters = Field(default_factory=AdvancedSearchFilters)
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1000000)


class AdvancedSearchResponse(BaseModel):
    ids: list[str]
    total: int
    corrected_query: str | None = None


class SearchRequest(BaseModel):
    query: str
    filters: SearchFilters = Field(default_factory=SearchFilters)
    page: int = 1
    page_size: int = 10
    limit: int | None = Field(default=None, ge=1, le=100, strict=True)
    offset: int | None = Field(default=None, ge=0, le=1000000, strict=True)
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
