"""RapidFuzz wrappers with safe fallbacks."""

from __future__ import annotations

from difflib import SequenceMatcher

try:
    from rapidfuzz import fuzz, process
except Exception:  # pragma: no cover
    fuzz = None
    process = None


def similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if fuzz is not None:
        return float(fuzz.ratio(left, right)) / 100.0
    return SequenceMatcher(None, left, right).ratio()


def partial_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if fuzz is not None:
        return float(fuzz.partial_ratio(left, right)) / 100.0
    return SequenceMatcher(None, left, right).ratio()


def token_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if fuzz is not None:
        return float(fuzz.token_set_ratio(left, right)) / 100.0
    return SequenceMatcher(None, left, right).ratio()


def best_matches(query: str, choices: list[str], limit: int = 5) -> list[tuple[str, float]]:
    if not query or not choices:
        return []
    if process is not None:
        results = process.extract(query, choices, scorer=fuzz.token_set_ratio, limit=limit)
        return [(choice, float(score) / 100.0) for choice, score, _ in results]
    scored = sorted(
        ((choice, SequenceMatcher(None, query, choice).ratio()) for choice in choices),
        key=lambda item: item[1],
        reverse=True,
    )
    return scored[:limit]
