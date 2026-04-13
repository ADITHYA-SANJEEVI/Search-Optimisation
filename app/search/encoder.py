"""Semantic encoder abstraction with local fallbacks."""

from __future__ import annotations

import logging
from collections import Counter

from app.core.config import settings
from app.utils.text import build_weighted_counter, counter_cosine

logger = logging.getLogger(__name__)


class SemanticEncoder:
    """Thin abstraction around semantic encoding."""

    def __init__(self) -> None:
        self._model = None
        if settings.enable_semantic_search:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore

                self._model = SentenceTransformer(
                    "sentence-transformers/all-MiniLM-L6-v2",
                    local_files_only=True,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("Local semantic model load failed, retrying with remote resolution: %s", exc)
                try:
                    from sentence_transformers import SentenceTransformer  # type: ignore

                    self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                except Exception as remote_exc:
                    logger.warning("Semantic model unavailable, falling back to local encoder: %s", remote_exc)

    @property
    def available(self) -> bool:
        return self._model is not None or settings.enable_semantic_search

    def encode(self, text: str) -> dict[str, float]:
        if self._model is not None:
            vector = self._model.encode(text)
            return {str(index): float(value) for index, value in enumerate(vector.tolist())}
        return {key: float(value) for key, value in build_weighted_counter(text).items()}

    def similarity(self, left: dict[str, float], right: dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        return counter_cosine(Counter(left), Counter(right))
