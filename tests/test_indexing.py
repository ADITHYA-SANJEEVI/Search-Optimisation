from __future__ import annotations

from app.schemas.indexing import CourseDocumentPayload
from app.schemas.search import SearchRequest


def test_index_update_is_idempotent(container) -> None:
    document = CourseDocumentPayload(
        course_id="course-test-001",
        group_id="grp-test-001",
        title="Breastfeeding Booster Session",
        aliases=["Lactation Booster"],
        synonyms=["breastfeeding support"],
        transliterations=[],
        description="Extra support for breastfeeding technique and confidence.",
        tags=["breastfeeding", "support"],
        instructor="Dr. Test",
        language="English",
        available_languages=["English"],
        category="Maternal Health",
        topic="Breastfeeding",
        difficulty="beginner",
        duration_minutes=45,
        certification=False,
        popularity_score=0.2,
        recency_score=0.9,
    )
    container.index_service.update(document)
    container.index_service.update(document)
    response = container.search_service.search(SearchRequest(query="booster breastfeeding"))
    assert response.results
    assert response.results[0].course_id == "course-test-001"


def test_delete_removes_course(container) -> None:
    deleted = container.index_service.delete(["dual-task-therapy-en"])
    assert deleted == 1
    response = container.search_service.search(SearchRequest(query="dual task therapy"))
    assert all(result.course_id != "dual-task-therapy-en" for result in response.results)
