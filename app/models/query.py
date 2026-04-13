"""Internal query-state models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class QueryIntent:
    topics: list[str] = field(default_factory=list)
    specialties: list[str] = field(default_factory=list)
    language_preferences: list[str] = field(default_factory=list)
    difficulty: str | None = None
    intent_type: str = "course_discovery"
    educational_goal: str | None = None
    summary: str | None = None


@dataclass(slots=True)
class RepairedQuery:
    text: str
    confidence: float
    source: str


@dataclass(slots=True)
class QueryState:
    original_query: str
    normalized_query: str
    compact_query: str
    normalized_tokens: list[str]
    expanded_terms: list[str]
    detected_languages: list[str]
    is_code_mixed: bool
    repaired_candidates: list[RepairedQuery]
    corrected_query: str | None
    did_you_mean: str | None
    search_instead_for: str | None
    intent: QueryIntent
    applied_filters: dict[str, object]
    debug: dict[str, object] = field(default_factory=dict)
