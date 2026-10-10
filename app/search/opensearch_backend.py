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
            raise RuntimeError("opensearch-py is required for the configured backend")
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
            mappings = self.client.indices.get_mapping(index=settings.opensearch_index)
            mapping = mappings[settings.opensearch_index]["mappings"]
            properties = mapping.get("properties", {})
            if (mapping.get("dynamic") != "strict" or
                properties.get("course_id", {}).get("type") != "keyword" or
                properties.get("updated_on", {}).get("type") != "date" or
                properties.get("metadata", {}).get("enabled") is not False):
                raise RuntimeError("Incompatible OpenSearch mapping; configure a new index and full-sync it")
            return
        self.client.indices.create(
            index=settings.opensearch_index,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
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
                    "dynamic": "strict",
                    "date_detection": False,
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
                        "content_type": {"type": "keyword"},
                        "publication_status": {"type": "keyword"},
                        "topic": {"type": "keyword"},
                        "competency_name": {"type": "text"},
                        "levels": {"type": "keyword"},
                        "updated_on": {"type": "date", "format": "strict_date_optional_time||MMM d, yyyy"},
                        "difficulty": {"type": "keyword"},
                        "duration_minutes": {"type": "integer", "coerce": False},
                        "certification": {"type": "boolean"},
                        "popularity_score": {"type": "float", "coerce": False},
                        "recency_score": {"type": "float", "coerce": False},
                        "active": {"type": "boolean"},
                        "searchable_metadata": {"type": "text"},
                        "metadata": {"type": "object", "enabled": False},
                    }
                },
            },
        )

    def _serialize(self, document: CourseDocumentPayload) -> dict[str, Any]:
        body = document.model_dump()
        body["group_id"] = document.group_id or document.course_id
        if document.updated_on:
            from app.utils.dates import parse_date
            body["updated_on"] = parse_date(document.updated_on).isoformat()
        return body

    def _reload_cache(self) -> None:
        if self.client is None:
            return
        hits = helpers.scan(self.client, index=settings.opensearch_index,
                            query={"query": {"match_all": {}}}, size=500)
        documents = {}
        for hit in hits:
            document = CourseDocumentPayload(**hit["_source"])
            if hit["_id"] != document.course_id:
                raise RuntimeError("Index identity does not match canonical course ID")
            documents[hit["_id"]] = self._prepare_document(document)
        self._documents = documents
        self._recompute_stats()
        self._invalidate_caches()

    def bulk_upsert(self, documents: list[CourseDocumentPayload]) -> int:
        if self.client is None or helpers is None:
            raise RuntimeError("OpenSearch client unavailable")
        if not documents:
            return 0
        actions = [
            {
                "_op_type": "index",
                "_index": settings.opensearch_index,
                "_id": document.course_id,
                "_source": self._serialize(document),
            }
            for document in documents
        ]
        try:
            helpers.bulk(self.client, actions)
            self.client.indices.refresh(index=settings.opensearch_index)
        except Exception:
            # Bulk failures may have persisted a subset; never keep a false local snapshot.
            self._reload_cache()
            raise
        return super().bulk_upsert(documents)

    def upsert_one(self, document: CourseDocumentPayload) -> None:
        self.bulk_upsert([document])

    def delete_many(self, course_ids: list[str]) -> int:
        if self.client is None or not course_ids:
            return 0
        actions = [
            {"_op_type": "delete", "_index": settings.opensearch_index, "_id": course_id}
            for course_id in course_ids
        ]
        if helpers is not None:
            helpers.bulk(self.client, actions, ignore_status=(404,))
            self.client.indices.refresh(index=settings.opensearch_index)
        return super().delete_many(course_ids)

    def health_details(self) -> dict[str, Any]:
        if self.client is None:
            return {"status": "degraded", "reason": "client_unavailable"}
        try:
            response = self.client.cluster.health()
            exists = self.client.indices.exists(index=settings.opensearch_index)
            count = self.client.count(index=settings.opensearch_index)["count"] if exists else 0
            usable = exists and response.get("status") in {"green", "yellow"} and count == self.document_count()
            return {"status": "up" if usable else "down", "cluster_status": response.get("status"),
                    "index_exists": exists, "index_document_count": count}
        except Exception as exc:  # pragma: no cover
            return {"status": "down", "reason": type(exc).__name__}
