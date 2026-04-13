"""OpenSearch-backed backend with local cache for reranking."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.search.backend import InMemorySearchBackend
from app.search.encoder import SemanticEncoder
from app.schemas.indexing import CourseDocumentPayload

logger = logging.getLogger(__name__)

try:
    from opensearchpy import OpenSearch, helpers  # type: ignore
except Exception:  # pragma: no cover
    OpenSearch = None
    helpers = None


class OpenSearchBackedSearchBackend(InMemorySearchBackend):
    """Persists documents in OpenSearch while keeping an in-process cache for scoring."""

    def __init__(self, encoder: SemanticEncoder) -> None:
        super().__init__(encoder=encoder)
        self.client = None
        if OpenSearch is None:
            logger.warning("opensearch-py unavailable, OpenSearch backend cannot be enabled")
            return
        self.client = OpenSearch(
            hosts=[settings.opensearch_url],
            verify_certs=settings.opensearch_verify_certs,
            ssl_show_warn=False,
            use_ssl=settings.opensearch_url.startswith("https://"),
            timeout=settings.opensearch_timeout_seconds,
        )
        self._ensure_index()
        self._reload_cache()

    def _ensure_index(self) -> None:
        if self.client is None:
            return
        if self.client.indices.exists(index=settings.opensearch_index):
            return
        self.client.indices.create(
            index=settings.opensearch_index,
            body={
                "settings": {
                    "analysis": {
                        "normalizer": {
                            "lowercase_normalizer": {
                                "type": "custom",
                                "char_filter": [],
                                "filter": ["lowercase", "asciifolding"],
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "course_id": {"type": "keyword"},
                        "group_id": {"type": "keyword"},
                        "title": {"type": "text"},
                        "aliases": {"type": "text"},
                        "synonyms": {"type": "text"},
                        "transliterations": {"type": "text"},
                        "description": {"type": "text"},
                        "tags": {"type": "keyword"},
                        "instructor": {"type": "text"},
                        "language": {"type": "keyword", "normalizer": "lowercase_normalizer"},
                        "available_languages": {"type": "keyword", "normalizer": "lowercase_normalizer"},
                        "category": {"type": "keyword"},
                        "topic": {"type": "keyword"},
                        "competency_name": {"type": "text"},
                        "levels": {"type": "keyword"},
                        "updated_on": {"type": "date", "format": "strict_date_optional_time||MMM d, yyyy"},
                        "difficulty": {"type": "keyword"},
                        "duration_minutes": {"type": "integer"},
                        "certification": {"type": "boolean"},
                        "popularity_score": {"type": "float"},
                        "recency_score": {"type": "float"},
                        "active": {"type": "boolean"},
                        "metadata": {"type": "object", "enabled": True},
                    }
                },
            },
        )

    def _serialize(self, document: CourseDocumentPayload) -> dict[str, Any]:
        body = document.model_dump()
        body["group_id"] = document.group_id or document.course_id
        return body

    def _reload_cache(self) -> None:
        if self.client is None:
            return
        response = self.client.search(
            index=settings.opensearch_index,
            body={"query": {"match_all": {}}, "size": 10000},
        )
        hits = response.get("hits", {}).get("hits", [])
        self._documents.clear()
        for hit in hits:
            self._documents[hit["_id"]] = self._prepare_document(CourseDocumentPayload(**hit["_source"]))
        self._recompute_stats()

    def bulk_upsert(self, documents: list[CourseDocumentPayload]) -> int:
        indexed = super().bulk_upsert(documents)
        if self.client is None or helpers is None:
            return indexed
        actions = [
            {
                "_op_type": "index",
                "_index": settings.opensearch_index,
                "_id": document.course_id,
                "_source": self._serialize(document),
            }
            for document in documents
        ]
        helpers.bulk(self.client, actions)
        self.client.indices.refresh(index=settings.opensearch_index)
        return indexed

    def upsert_one(self, document: CourseDocumentPayload) -> None:
        super().upsert_one(document)
        if self.client is None:
            return
        self.client.index(
            index=settings.opensearch_index,
            id=document.course_id,
            body=self._serialize(document),
            refresh=True,
        )

    def delete_many(self, course_ids: list[str]) -> int:
        deleted = super().delete_many(course_ids)
        if self.client is None or not course_ids:
            return deleted
        actions = [
            {"_op_type": "delete", "_index": settings.opensearch_index, "_id": course_id}
            for course_id in course_ids
        ]
        if helpers is not None:
            helpers.bulk(self.client, actions, raise_on_error=False)
            self.client.indices.refresh(index=settings.opensearch_index)
        return deleted

    def health_details(self) -> dict[str, Any]:
        if self.client is None:
            return {"status": "degraded", "reason": "client_unavailable"}
        try:
            response = self.client.cluster.health()
            return {"status": response.get("status", "unknown"), "cluster_name": response.get("cluster_name")}
        except Exception as exc:  # pragma: no cover
            return {"status": "down", "reason": str(exc)}
