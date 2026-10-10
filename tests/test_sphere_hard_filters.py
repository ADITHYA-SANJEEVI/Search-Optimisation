from __future__ import annotations

from app.schemas.indexing import CourseDocumentPayload
from app.schemas.search import SearchRequest


def _document(course_id: str, *, category: str, content_type: str, status: str) -> CourseDocumentPayload:
    return CourseDocumentPayload(
        course_id=course_id,
        title="Sphere filter verification course",
        description="Synthetic record for exact hard-filter verification.",
        instructor="",
        language="English",
        available_languages=["English"],
        category=category,
        content_type=content_type,
        publication_status=status,
        topic="Filter verification",
    )


def test_hard_filters_exclude_records_before_pagination(container) -> None:
    container.index_service.bulk_index(
        [
            _document("filter-live-course", category="Course", content_type="Course", status="Live"),
            _document("filter-draft-course", category="Course", content_type="Course", status="Draft"),
            _document("filter-live-resource", category="Resource", content_type="LearningResource", status="Live"),
        ]
    )

    response = container.search_service.search(
        SearchRequest(
            query="Sphere filter verification course",
            filters={
                "categories": ["Course"],
                "content_types": ["Course"],
                "publication_statuses": ["Live"],
            },
            page_size=1,
        )
    )

    assert [result.course_id for result in response.results] == ["filter-live-course"]
    assert response.pagination.total_results == 1
    assert response.pagination.total_pages == 1


def test_existing_search_contract_remains_compatible(client) -> None:
    response = client.post("/api/v1/search", json={"query": "breastfeeding"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert "course_id" in payload["results"][0]
