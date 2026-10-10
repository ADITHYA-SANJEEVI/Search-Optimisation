from __future__ import annotations

import pytest

from app.integrations.sphere_request import SphereRequestValidationError, translate_sphere_request


def _request(**overrides):
    payload = {
        "request": {
            "query": "pregnancy",
            "filters": {
                "primaryCategory": ["Course"],
                "contentType": ["Course"],
                "status": ["Live"],
            },
        },
        "query": "pregnancy",
        "sort": [],
    }
    payload.update(overrides)
    return payload


def test_equivalent_duplicate_queries_and_hard_filters_translate() -> None:
    translated = translate_sphere_request(_request())

    assert translated.search_request.query == "pregnancy"
    assert translated.search_request.sort == "relevance"
    assert translated.search_request.filters.categories == ["Course"]
    assert translated.search_request.filters.content_types == ["Course"]
    assert translated.search_request.filters.publication_statuses == ["Live"]


def test_single_nonblank_query_is_accepted_but_conflicts_are_rejected() -> None:
    translated = translate_sphere_request(_request(query="  "))
    assert translated.search_request.query == "pregnancy"

    with pytest.raises(SphereRequestValidationError) as error:
        translate_sphere_request(_request(query="nutrition"))
    assert error.value.code == "conflicting_query"


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (_request(request={"query": "pregnancy", "filters": {"status": "Live"}}), "invalid_filter_shape"),
        (_request(request={"query": "pregnancy", "filters": {"unknown": ["x"]}}), "unsupported_filter"),
        (_request(sort={"lastUpdatedOn": "desc"}), "invalid_sort_shape"),
        (_request(sort=[{"name": "asc"}]), "unsupported_sort"),
        (_request(page=2), "unsupported_pagination"),
    ],
)
def test_malformed_or_unsupported_request_parts_are_rejected(payload, code: str) -> None:
    with pytest.raises(SphereRequestValidationError) as error:
        translate_sphere_request(payload)
    assert error.value.code == code


def test_pagination_and_query_vs_browse_sort_policy():
    query = translate_sphere_request(_request(sort=[{"lastUpdatedOn": "desc"}], limit=3, offset=2))
    assert query.search_request.sort == "relevance"
    assert (query.search_request.limit, query.search_request.offset) == (3, 2)
    browse = translate_sphere_request({"request": {"query": " ", "limit": 2, "offset": 4},
                                       "sort": [{"lastUpdatedOn": "desc"}]})
    assert browse.search_request.query == ""
    assert browse.search_request.sort == "newest"
