"""Persistent analytics storage."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SQLiteAnalyticsStore:
    """SQLite-backed analytics sink. Failures are non-fatal to search flows."""

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS search_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    query_text TEXT NOT NULL,
                    normalized_query TEXT,
                    corrected_query TEXT,
                    route_type TEXT NOT NULL,
                    result_count INTEGER NOT NULL,
                    latency_ms REAL NOT NULL,
                    zero_results INTEGER NOT NULL DEFAULT 0,
                    degraded INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT
                );

                CREATE TABLE IF NOT EXISTS correction_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    original_query TEXT NOT NULL,
                    corrected_query TEXT NOT NULL,
                    route_type TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS zero_result_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    query_text TEXT NOT NULL,
                    normalized_query TEXT,
                    route_type TEXT NOT NULL,
                    metadata_json TEXT
                );
                """
            )

    def record_search_event(
        self,
        *,
        query_text: str,
        normalized_query: str | None,
        corrected_query: str | None,
        route_type: str,
        result_count: int,
        latency_ms: float,
        zero_results: bool,
        degraded: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        payload = json.dumps(metadata or {}, ensure_ascii=False)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO search_events
                (query_text, normalized_query, corrected_query, route_type, result_count, latency_ms, zero_results, degraded, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_text,
                    normalized_query,
                    corrected_query,
                    route_type,
                    result_count,
                    latency_ms,
                    int(zero_results),
                    int(degraded),
                    payload,
                ),
            )
            if zero_results:
                connection.execute(
                    """
                    INSERT INTO zero_result_events (query_text, normalized_query, route_type, metadata_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (query_text, normalized_query, route_type, payload),
                )

    def record_correction_event(self, *, original_query: str, corrected_query: str, route_type: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO correction_events (original_query, corrected_query, route_type)
                VALUES (?, ?, ?)
                """,
                (original_query, corrected_query, route_type),
            )

    def recent_search_events(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM search_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def health_details(self) -> dict[str, Any]:
        try:
            with self._lock, self._connect() as connection:
                count = connection.execute("SELECT COUNT(*) FROM search_events").fetchone()[0]
            return {"status": "up", "details": {"db_path": str(self.db_path), "search_event_count": count}}
        except Exception as exc:  # pragma: no cover
            logger.warning("Analytics store health check failed: %s", exc)
            return {"status": "degraded", "details": {"reason": str(exc), "db_path": str(self.db_path)}}
