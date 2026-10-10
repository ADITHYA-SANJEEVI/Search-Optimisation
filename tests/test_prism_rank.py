from __future__ import annotations

from app.schemas.search import SearchRequest


def test_prism_rank_exposes_named_explainable_signal_breakdown(container) -> None:
    response = container.search_service.search(SearchRequest(query="beginner pregnancy nutrition in Hindi", debug=True))

    assert response.results
    best = response.results[0]
    assert best.group_id == "safe-pregnancy-anc"
    assert best.debug["algorithm"] == "Aastrika PRISM Rank"
    assert best.debug["attribute"] > 0
    assert best.debug["quality"] > 0
    assert "Structured course attributes match the request" in best.explanations


def test_prism_rank_penalizes_conflicting_difficulty(container) -> None:
    response = container.search_service.search(SearchRequest(query="beginner high risk pregnancy", debug=True))

    assert response.results
    conflicted = next(item for item in response.results if item.group_id == "high-risk-pregnancy")
    assert conflicted.debug["conflict_penalty"] > 0
    assert "Some requested attributes conflict with this course" in conflicted.explanations


def test_prism_rank_handles_unrelated_descriptions_gracefully(container) -> None:
    response = container.search_service.search(SearchRequest(query="quantum astrophysics for toddlers", debug=True))

    assert response.results == []
    assert response.no_results_guidance is not None


def test_prism_rank_tie_breaks_similar_candidates_with_specific_evidence(container) -> None:
    response = container.search_service.search(SearchRequest(query="advanced breastfeeding assessment counselling", debug=True))

    assert response.results
    assert response.results[0].course_id == "counsels-breastfeeding-assessment-en"
    assert response.results[0].score > response.results[1].score
