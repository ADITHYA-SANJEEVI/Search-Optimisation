"""Search analytics hooks and lightweight metrics."""

from __future__ import annotations

import logging
from collections import Counter, deque
from time import perf_counter
from typing import Any

from app.analytics.storage import SQLiteAnalyticsStore

logger = logging.getLogger(__name__)


class AnalyticsTracker:
    def __init__(self, store: SQLiteAnalyticsStore | None = None) -> None:
        self.query_counter: Counter[str] = Counter()
        self.zero_result_queries: deque[str] = deque(maxlen=200)
        self.corrections: deque[tuple[str, str]] = deque(maxlen=200)
        self.latencies_ms: deque[float] = deque(maxlen=500)
        self.store = store

    def start_timer(self) -> float:
        return perf_counter()

    def record_search(
        self,
        query: str,
        result_count: int,
        latency_ms: float,
        *,
        normalized_query: str | None = None,
        corrected_query: str | None = None,
        route_type: str = "search",
        degraded: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.query_counter[query] += 1
        self.latencies_ms.append(latency_ms)
        logger.info(
            "search query=%s route_type=%s result_count=%s latency_ms=%.2f",
            query,
            route_type,
            result_count,
            latency_ms,
        )
        zero_results = result_count == 0
        if zero_results:
            self.zero_result_queries.append(query)
        if self.store is not None:
            try:
                self.store.record_search_event(
                    query_text=query,
                    normalized_query=normalized_query,
                    corrected_query=corrected_query,
                    route_type=route_type,
                    result_count=result_count,
                    latency_ms=latency_ms,
                    zero_results=zero_results,
                    degraded=degraded,
                    metadata=metadata,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("analytics_store_search_write_failed: %s", exc)

    def record_correction(self, original: str, corrected: str, *, route_type: str = "search") -> None:
        self.corrections.append((original, corrected))
        logger.info("query_correction route_type=%s original=%s corrected=%s", route_type, original, corrected)
        if self.store is not None:
            try:
                self.store.record_correction_event(
                    original_query=original,
                    corrected_query=corrected,
                    route_type=route_type,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning("analytics_store_correction_write_failed: %s", exc)

    def dependencies_status(self) -> list[dict[str, object]]:
        avg_latency = sum(self.latencies_ms) / len(self.latencies_ms) if self.latencies_ms else 0.0
        statuses = [
            {"name": "analytics", "status": "up", "details": {"avg_latency_ms": round(avg_latency, 2)}},
        ]
        if self.store is not None:
            statuses.append({"name": "analytics_store", **self.store.health_details()})
        return statuses
