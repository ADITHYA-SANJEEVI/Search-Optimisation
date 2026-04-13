"""Internal course document models."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class IndexedCourse:
    course_id: str
    group_id: str
    title: str
    title_normalized: str
    title_no_spaces: str
    aliases: list[str]
    aliases_normalized: list[str]
    synonyms: list[str]
    transliterations: list[str]
    description: str
    description_normalized: str
    tags: list[str]
    instructor: str
    instructor_normalized: str
    language: str
    available_languages: list[str]
    category: str
    topic: str
    competency_name: str | None
    levels: list[str]
    updated_on: str | None
    difficulty: str | None
    duration_minutes: int | None
    certification: bool | None
    popularity_score: float
    recency_score: float
    active: bool
    metadata: dict[str, Any]
    suggestion_terms: list[str]
    semantic_text: str
    semantic_vector: dict[str, float]
    title_terms: list[str]
    all_terms: list[str]
    title_frequencies: Counter[str] = field(default_factory=Counter)
    all_frequencies: Counter[str] = field(default_factory=Counter)


@dataclass(slots=True)
class SearchCandidate:
    course: IndexedCourse
    lexical_score: float
    title_bm25_score: float
    fuzzy_score: float
    phrase_score: float
    semantic_score: float
    phonetic_score: float
    language_boost: float
    popularity_score: float
    recency_score: float
    matched_terms: list[str]
    explanations: list[str]
    score_breakdown: dict[str, float]
