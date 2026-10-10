"""Translate the verified Sphere request structure into the internal search contract."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.search import SearchFilters, SearchRequest
from app.schemas.sphere import SphereRequestTranslation


class SphereRequestValidationError(ValueError):
    def __init__(self, code: str, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


def _query_value(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SphereRequestValidationError("invalid_query_type", f"{field} must be a string", field=field)
    value = value.strip()
    return value or None


def _filter_values(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise SphereRequestValidationError(
            "invalid_filter_shape", f"{field} must be an array of strings", field=field
        )
    parsed: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise SphereRequestValidationError(
                "invalid_filter_value", f"{field} must contain only nonblank strings", field=field
            )
        normalized = item.strip()
        if normalized.casefold() not in {existing.casefold() for existing in parsed}:
            parsed.append(normalized)
    return parsed


def translate_sphere_request(payload: object) -> SphereRequestTranslation:
    if not isinstance(payload, Mapping):
        raise SphereRequestValidationError("invalid_request_type", "Sphere request must be an object")

    pagination_fields = {"page", "pageSize", "cursor"}
    present_pagination = sorted(pagination_fields & set(payload))
    if present_pagination:
        raise SphereRequestValidationError(
            "unsupported_pagination",
            f"Unsupported Sphere pagination field(s): {', '.join(present_pagination)}",
            field=present_pagination[0],
        )
    allowed_top_level = {"request", "query", "sort", "limit", "offset"}
    unknown_top_level = sorted(set(payload) - allowed_top_level)
    if unknown_top_level:
        raise SphereRequestValidationError(
            "unknown_request_field",
            f"Unknown top-level field(s): {', '.join(unknown_top_level)}",
            field=unknown_top_level[0],
        )

    nested = payload.get("request", {})
    if not isinstance(nested, Mapping):
        raise SphereRequestValidationError("invalid_nested_request", "request must be an object", field="request")
    unknown_nested = sorted(set(nested) - {"query", "filters", "limit", "offset"})
    if unknown_nested:
        raise SphereRequestValidationError(
            "unknown_nested_field",
            f"Unknown request field(s): {', '.join(unknown_nested)}",
            field=f"request.{unknown_nested[0]}",
        )

    nested_query = _query_value(nested.get("query"), "request.query")
    top_query = _query_value(payload.get("query"), "query")
    if nested_query and top_query and nested_query != top_query:
        raise SphereRequestValidationError(
            "conflicting_query", "request.query and query contain different nonblank values", field="query"
        )
    query = nested_query or top_query
    query = query or ""

    raw_filters = nested.get("filters", {})
    if not isinstance(raw_filters, Mapping):
        raise SphereRequestValidationError(
            "invalid_filters_type", "request.filters must be an object", field="request.filters"
        )
    supported_filters = {"primaryCategory", "contentType", "status"}
    unknown_filters = sorted(set(raw_filters) - supported_filters)
    if unknown_filters:
        raise SphereRequestValidationError(
            "unsupported_filter",
            f"Unsupported Sphere filter(s): {', '.join(unknown_filters)}",
            field=f"request.filters.{unknown_filters[0]}",
        )
    parsed_filters = {
        field: _filter_values(raw_filters[field], f"request.filters.{field}")
        for field in supported_filters
        if field in raw_filters
    }

    raw_sort = payload.get("sort", [])
    if not isinstance(raw_sort, list):
        raise SphereRequestValidationError("invalid_sort_shape", "sort must be an array", field="sort")
    if raw_sort and raw_sort != [{"lastUpdatedOn": "desc"}]:
        raise SphereRequestValidationError(
            "unsupported_sort", "The requested Sphere sort is not supported", field="sort"
        )

    filters = SearchFilters(
        categories=parsed_filters.get("primaryCategory", []),
        content_types=parsed_filters.get("contentType", []),
        publication_statuses=parsed_filters.get("status", []),
    )
    pagination = {}
    for key, default, low, high in (("limit", 10, 1, 100), ("offset", 0, 0, 1000000)):
        if key in nested and key in payload and nested[key] != payload[key]:
            raise SphereRequestValidationError("conflicting_pagination", f"Conflicting {key}", field=key)
        value = nested.get(key, payload.get(key, default))
        if type(value) is not int or not low <= value <= high:
            raise SphereRequestValidationError("invalid_pagination", f"Invalid {key}", field=key)
        pagination[key] = value
    return SphereRequestTranslation(
        search_request=SearchRequest(query=query, filters=filters, sort="relevance" if query else "newest", **pagination),
        source_query_fields={"request.query": nested_query, "query": top_query},
        source_filters=parsed_filters,
        source_sort=raw_sort,
    )
