"""Aastrika-specific ranking and confidence calculation."""

from __future__ import annotations

from app.core.config import settings
from app.models.course import SearchCandidate


class AastrikaPrismRanker:
    """Explainable weighted scorer for Aastrika course discovery.

    PRISM stands for Precision, Relevance, Intent, Signal quality, and Metadata.
    The ranker keeps textual retrieval dominant while allowing structured course
    attributes and catalog quality to break close ties.
    """

    algorithm_name = "Aastrika PRISM Rank"

    def score(self, candidate: SearchCandidate) -> float:
        weights = settings.weights
        total = (
            candidate.lexical_score * weights["bm25"]
            + candidate.title_bm25_score * weights["title_bm25"]
            + candidate.fuzzy_score * weights["fuzzy"]
            + candidate.semantic_score * weights["semantic"]
            + candidate.phrase_score * weights["phrase"]
            + candidate.phonetic_score * weights["phonetic"]
            + candidate.language_boost * weights["language_boost"]
            + candidate.attribute_score * weights["attribute"]
            + candidate.contextual_score * weights["contextual"]
            + candidate.quality_score * weights["quality"]
            + candidate.popularity_score * weights["popularity"]
            + candidate.recency_score * weights["recency"]
            - candidate.conflict_penalty * weights["conflict_penalty"]
        )
        candidate.score_breakdown = {
            "algorithm": self.algorithm_name,
            "lexical": round(candidate.lexical_score, 4),
            "title_bm25": round(candidate.title_bm25_score, 4),
            "fuzzy": round(candidate.fuzzy_score, 4),
            "semantic": round(candidate.semantic_score, 4),
            "phrase": round(candidate.phrase_score, 4),
            "phonetic": round(candidate.phonetic_score, 4),
            "language_boost": round(candidate.language_boost, 4),
            "attribute": round(candidate.attribute_score, 4),
            "contextual": round(candidate.contextual_score, 4),
            "quality": round(candidate.quality_score, 4),
            "conflict_penalty": round(candidate.conflict_penalty, 4),
            "popularity": round(candidate.popularity_score, 4),
            "recency": round(candidate.recency_score, 4),
            "total": round(total, 4),
        }
        return total

    def confidence(self, candidate: SearchCandidate) -> float:
        score = candidate.score_breakdown.get("total", 0.0)
        if candidate.conflict_penalty >= 0.6:
            return max(0.15, min(0.72, 0.3 + score / 6.0))
        if candidate.phrase_score >= 1.2:
            return min(0.99, 0.7 + score / 4.0)
        if candidate.fuzzy_score >= 0.9 and candidate.semantic_score >= 0.3:
            return min(0.95, 0.62 + score / 4.5)
        return max(0.15, min(0.9, 0.35 + score / 5.0))


HybridReranker = AastrikaPrismRanker
