"""Helpers for validating the live OpenSearch adapter path."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.schemas.search import SearchRequest
from app.services.bootstrap import build_container


@contextmanager
def opensearch_container_env():
    previous_backend = settings.search_backend
    settings.search_backend = "opensearch"
    try:
        container = build_container()
        app.state.container = container
        yield container
    finally:
        settings.search_backend = previous_backend


def run_opensearch_smoke_validation() -> dict[str, Any]:
    with opensearch_container_env() as container:
        backend_name = type(container.backend).__name__
        assert backend_name == "OpenSearchBackedSearchBackend", backend_name
        backend_health = container.backend.health_details() if hasattr(container.backend, "health_details") else {}
        search_response = container.search_service.search(SearchRequest(query="pph assessment"))
        suggest_response = container.suggester.suggest("pph", "Hindi", limit=5)
        original_count = container.backend.document_count()

        container.index_service.update(
            SearchFixtureDocumentFactory.make_document(course_id="smoke-course-001", title="Smoke Test Course")
        )
        updated_count = container.backend.document_count()
        container.index_service.delete(["smoke-course-001"])
        deleted_count = container.backend.document_count()

        with TestClient(app) as client:
            search_api = client.post(
                "/api/v1/search",
                json={"query": "emergency triage"},
                headers={settings.api_key_header_name: os.getenv("API_KEYS", "dev-search-key").split(",")[0].strip()},
            )
            suggest_api = client.get(
                "/api/v1/suggest",
                params={"q": "pph"},
                headers={settings.api_key_header_name: os.getenv("API_KEYS", "dev-search-key").split(",")[0].strip()},
            )
        return {
            "backend": backend_name,
            "backend_health": backend_health,
            "initial_document_count": original_count,
            "post_update_document_count": updated_count,
            "post_delete_document_count": deleted_count,
            "search_top_group_id": search_response.results[0].group_id if search_response.results else None,
            "suggest_sections": [group.section for group in suggest_response],
            "api_search_status_code": search_api.status_code,
            "api_suggest_status_code": suggest_api.status_code,
            "index_exists": bool(backend_health),
        }


class SearchFixtureDocumentFactory:
    @staticmethod
    def make_document(course_id: str, title: str):
        from app.schemas.indexing import CourseDocumentPayload

        return CourseDocumentPayload(
            course_id=course_id,
            group_id=course_id,
            title=title,
            aliases=[title],
            synonyms=["smoke test"],
            transliterations=[],
            description="Temporary smoke-test document.",
            tags=["smoke"],
            instructor="Smoke Runner",
            language="English",
            available_languages=["English"],
            category="Testing",
            topic="Smoke Validation",
            competency_name="Smoke Validation",
            levels=["Level 1"],
            updated_on="Apr 11, 2026",
            difficulty="beginner",
            duration_minutes=5,
            certification=False,
            popularity_score=0.1,
            recency_score=0.1,
            metadata={"smoke": True},
        )
