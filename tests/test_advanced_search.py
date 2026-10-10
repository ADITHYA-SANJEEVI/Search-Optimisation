import pytest

from app.main import app
from app.schemas.indexing import CourseDocumentPayload


@pytest.fixture()
def sphere_client(client):
    backend = app.state.container.backend
    backend.delete_many([d.course_id for d in backend.all_documents()])
    for identifier, title, date, language in [
        ("do_exact", "Pregnancy nutrition", "2025-01-01T00:00:00Z", "English"),
        ("do_new", "Pregnancy support", "2026-09-01T00:00:00Z", "Hindi"),
        ("do_tie", "Pregnancy support", "2026-09-01T00:00:00Z", "Hindi"),
        ("do_missing_date", "Pregnancy information", None, "English"),
    ]:
        backend.upsert_one(CourseDocumentPayload(course_id=identifier, title=title, description=title,
            instructor="", language=language, category="Course", publication_status="Live",
            content_type="Course", topic="Pregnancy", updated_on=date))
    return client


def test_ids_only_relevance_and_offset(sphere_client):
    request = {"query": "Pregnancy nutrition", "limit": 100}
    all_results = sphere_client.post("/v1/search", json=request).json()
    assert set(all_results) <= {"ids", "total", "corrected_query"}
    assert all_results["ids"][0] == "do_exact"  # Older exact title beats newer weak match.
    assert all(isinstance(id, str) for id in all_results["ids"])
    page = sphere_client.post("/v1/search", json={**request, "limit": 1, "offset": 1}).json()
    assert page["ids"] == all_results["ids"][1:2]
    assert page["total"] == all_results["total"]
    assert sphere_client.post("/v1/search", json=request).json() == all_results
    assert sphere_client.post("/v1/search", json={**request, "offset": all_results["total"]}).json()["ids"] == []
    assert sphere_client.post("/v1/search", json={**request, "sort": [{"lastUpdatedOn": "desc"}]}).status_code == 422


def test_browse_dates_ties_and_pages(sphere_client):
    expected = ["do_new", "do_tie", "do_exact", "do_missing_date"]
    for query in ({}, {"query": ""}, {"query": "  "}):
        result = sphere_client.post("/v1/search", json={**query, "limit": 100}).json()
        assert result == {"ids": expected, "total": 4}
    result = sphere_client.post("/v1/search", json={"offset": 1, "limit": 2}).json()
    assert result == {"ids": expected[1:3], "total": 4}


@pytest.mark.parametrize("query", ["", "Pregnancy support"])
def test_supported_filter_and_filtered_pagination(sphere_client, query):
    body = {"query": query, "filters": {"language": "Hindi", "primaryCategory": ["Course"],
             "status": ["Live"], "contentType": ["Course"]}, "limit": 1}
    first = sphere_client.post("/v1/search", json=body).json()
    second = sphere_client.post("/v1/search", json={**body, "offset": 1}).json()
    assert first == {"ids": ["do_new"], "total": 2}
    assert second == {"ids": ["do_tie"], "total": 2}
    assert sphere_client.post("/v1/search", json={"query": query, "filters": {"language": "French"}}).json()["total"] == 0


def test_empty_and_live_course_eligibility(sphere_client):
    assert sphere_client.post("/v1/search", json={"query": "quantum astrophysics for toddlers"}).json()["total"] == 0
    backend = app.state.container.backend
    doc = next(d for d in backend.all_documents() if d.course_id == "do_exact")
    backend._documents[doc.course_id].publication_status = "Draft"
    assert "do_exact" not in sphere_client.post("/v1/search", json={}).json()["ids"]


@pytest.mark.parametrize("body", [{"limit": 0}, {"limit": 101}, {"limit": "2"}, {"limit": True},
    {"offset": -1}, {"offset": 1000001}, {"offset": 1.5}, {"query": None}, {"query": "x" * 241},
    {"filters": {"unknown": ["x"]}}, {"filters": []}, {"filters": {"status": "Live"}}])
def test_invalid_contract(sphere_client, body):
    assert sphere_client.post("/v1/search", json=body).status_code == 422


@pytest.mark.parametrize("query,expected", [
    ("lactaion counsler", "lactation-counselor-program"),
    ("KMC", "kangaroo-mother-care"),
    ("I need a Hindi course on family planning and lam", "family-planning-lam"),
    ("beginner pregnancy nutrition in Hindi", "safe-pregnancy-anc"),
    ("Stage 4 monitoring of mother and newborn", "stage4-monitoring-danger-signs"),
    ("respectfulmaternitycare", "respectful-maternity-care"),
])
def test_existing_named_quality_cases_on_ids_boundary(client, query, expected):
    container = app.state.container
    for doc in container.backend.all_documents():
        doc.category = "Course"
        doc.publication_status = "Live"
    response = client.post("/v1/search", json={"query": query})
    assert response.status_code == 200
    assert response.json()["ids"]
    first = response.json()["ids"][0]
    assert container.backend._documents[first].group_id == expected


def test_backend_failure_readiness_and_liveness(sphere_client, monkeypatch):
    backend = app.state.container.backend
    monkeypatch.setattr(backend, "health_details", lambda: {"status": "down"}, raising=False)
    response = sphere_client.post("/v1/search", json={"query": "pregnancy"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "search_backend_unavailable"
    assert sphere_client.get("/api/v1/ready").status_code == 503
    assert sphere_client.get("/api/v1/live").status_code == 200
