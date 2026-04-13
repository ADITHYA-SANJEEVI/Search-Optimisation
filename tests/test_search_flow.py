from __future__ import annotations

from app.schemas.search import SearchRequest


def test_typo_recovery_returns_breastfeeding_course(container) -> None:
    response = container.search_service.search(SearchRequest(query="lactaion counsler"))
    assert response.results
    assert response.results[0].group_id == "lactation-counselor-program"
    assert response.corrected_query is not None


def test_spacing_recovery_returns_newborn_course(container) -> None:
    response = container.search_service.search(SearchRequest(query="respectfulmaternitycare"))
    assert response.results
    assert response.results[0].group_id == "respectful-maternity-care"


def test_natural_language_query_prefers_requested_language(container) -> None:
    response = container.search_service.search(
        SearchRequest(query="I need a Hindi course on family planning and lam", preferred_language="Hindi")
    )
    assert response.results
    assert response.results[0].group_id == "family-planning-lam"
    assert "hindi" in response.detected_languages


def test_postpartum_typo_rescue(container) -> None:
    response = container.search_service.search(SearchRequest(query="PPHHH primary management"))
    assert response.results
    assert response.results[0].group_id == "postpartum-hemorrhage"


def test_romanized_hindi_query_rescue(container) -> None:
    response = container.search_service.search(SearchRequest(query="sammanjanak matritva dekhbhal"))
    assert response.results
    assert response.results[0].group_id == "respectful-maternity-care"


def test_exact_query_does_not_force_correction(container) -> None:
    response = container.search_service.search(SearchRequest(query="Emergency triage assessment"))
    assert response.results
    assert response.corrected_query is None
    assert response.did_you_mean is None


def test_zero_result_guidance_is_present_for_unknown_query(container) -> None:
    response = container.search_service.search(SearchRequest(query="quantum astrophysics for toddlers"))
    assert response.results == []
    assert response.no_results_guidance is not None
