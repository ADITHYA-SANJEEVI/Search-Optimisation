from __future__ import annotations


def test_suggest_returns_grouped_course_titles(client) -> None:
    response = client.get("/api/v1/suggest", params={"q": "pph", "preferred_language": "Hindi"})
    assert response.status_code == 200
    payload = response.json()
    sections = {group["section"] for group in payload}
    assert "course_titles" in sections
    assert "language_aware" in sections


def test_suggest_surfaces_correction_bucket(client) -> None:
    response = client.get("/api/v1/suggest", params={"q": "lactaion counsler"})
    assert response.status_code == 200
    payload = response.json()
    assert any(group["section"] == "corrected_query" for group in payload)
