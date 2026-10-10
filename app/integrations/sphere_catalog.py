"""Convert untrusted Sphere catalogue records into internal course documents."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from app.schemas.indexing import CourseDocumentPayload
from app.schemas.sphere import SphereAdapterDiagnostic, SphereCatalogueConversion


def _nonblank_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    return normalized or None


def _optional_string(
    record: Mapping[str, Any],
    field: str,
    diagnostics: list[SphereAdapterDiagnostic],
    *,
    record_index: int,
    identifier: str | None,
) -> str | None:
    value = record.get(field)
    if value is None:
        return None
    parsed = _nonblank_string(value)
    if parsed is None and not isinstance(value, str):
        diagnostics.append(
            SphereAdapterDiagnostic(
                severity="warning",
                code="invalid_optional_type",
                message=f"Ignored non-string optional field '{field}'",
                record_index=record_index,
                identifier=identifier,
                field=field,
            )
        )
    return parsed


def _string_list(
    value: object,
    field: str,
    diagnostics: list[SphereAdapterDiagnostic],
    *,
    record_index: int,
    identifier: str | None,
    allow_scalar: bool = False,
) -> list[str]:
    if value is None:
        return []
    values: list[object]
    if isinstance(value, list):
        values = value
    elif allow_scalar and isinstance(value, str):
        values = [value]
    else:
        diagnostics.append(
            SphereAdapterDiagnostic(
                severity="warning",
                code="invalid_optional_type",
                message=f"Ignored field '{field}' because it was not an array of strings",
                record_index=record_index,
                identifier=identifier,
                field=field,
            )
        )
        return []

    parsed: list[str] = []
    invalid_items = 0
    for item in values:
        text = _nonblank_string(item)
        if text is None:
            if item is not None and item != "":
                invalid_items += 1
            continue
        if text.casefold() not in {existing.casefold() for existing in parsed}:
            parsed.append(text)
    if invalid_items:
        diagnostics.append(
            SphereAdapterDiagnostic(
                severity="warning",
                code="invalid_array_items",
                message=f"Ignored {invalid_items} non-string item(s) in '{field}'",
                record_index=record_index,
                identifier=identifier,
                field=field,
            )
        )
    return parsed


def _description(*values: str | None) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value.casefold() not in seen:
            parts.append(value)
            seen.add(value.casefold())
    return "\n\n".join(parts)


def _parse_competencies(
    raw: object,
    diagnostics: list[SphereAdapterDiagnostic],
    *,
    record_index: int,
    identifier: str,
) -> tuple[list[str], list[str]]:
    if raw in (None, ""):
        return [], []
    if not isinstance(raw, str):
        diagnostics.append(
            SphereAdapterDiagnostic(
                severity="warning",
                code="invalid_competency_type",
                message="Ignored competencies_v1 because it was not serialized JSON",
                record_index=record_index,
                identifier=identifier,
                field="competencies_v1",
            )
        )
        return [], []
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError):
        diagnostics.append(
            SphereAdapterDiagnostic(
                severity="warning",
                code="malformed_competency_json",
                message="Ignored malformed competencies_v1 JSON",
                record_index=record_index,
                identifier=identifier,
                field="competencies_v1",
            )
        )
        return [], []
    if not isinstance(decoded, list):
        diagnostics.append(
            SphereAdapterDiagnostic(
                severity="warning",
                code="invalid_competency_shape",
                message="Ignored competencies_v1 because its JSON value was not an array",
                record_index=record_index,
                identifier=identifier,
                field="competencies_v1",
            )
        )
        return [], []

    names: list[str] = []
    levels: list[str] = []
    for item in decoded:
        if not isinstance(item, Mapping):
            continue
        name = _nonblank_string(item.get("competencyName"))
        level = _nonblank_string(item.get("level"))
        if name and name.casefold() not in {value.casefold() for value in names}:
            names.append(name)
        if level and level.casefold() not in {value.casefold() for value in levels}:
            levels.append(level)
    return names, levels


def convert_sphere_record(record: object, record_index: int = 0) -> tuple[CourseDocumentPayload | None, list[SphereAdapterDiagnostic]]:
    diagnostics: list[SphereAdapterDiagnostic] = []
    if not isinstance(record, Mapping):
        return None, [
            SphereAdapterDiagnostic(
                severity="error",
                code="invalid_record_type",
                message="Catalogue record must be an object",
                record_index=record_index,
            )
        ]

    raw_identifier = record.get("identifier")
    identifier = raw_identifier if isinstance(raw_identifier, str) and raw_identifier.strip() else None
    title = _nonblank_string(record.get("name"))
    if identifier is None:
        diagnostics.append(
            SphereAdapterDiagnostic(
                severity="error",
                code="missing_identifier",
                message="Record cannot be indexed without a canonical identifier",
                record_index=record_index,
                field="identifier",
            )
        )
    if title is None:
        diagnostics.append(
            SphereAdapterDiagnostic(
                severity="error",
                code="missing_name",
                message="Record cannot be indexed without a course name",
                record_index=record_index,
                identifier=identifier,
                field="name",
            )
        )
    if identifier is None or title is None:
        return None, diagnostics

    subtitle = _optional_string(record, "subTitle", diagnostics, record_index=record_index, identifier=identifier)
    instructions = _optional_string(record, "instructions", diagnostics, record_index=record_index, identifier=identifier)
    languages = _string_list(
        record.get("language"),
        "language",
        diagnostics,
        record_index=record_index,
        identifier=identifier,
        allow_scalar=True,
    )
    tags = _string_list(
        record.get("keywords"),
        "keywords",
        diagnostics,
        record_index=record_index,
        identifier=identifier,
    )
    competency_names, levels = _parse_competencies(
        record.get("competencies_v1"), diagnostics, record_index=record_index, identifier=identifier
    )
    category = _optional_string(record, "primaryCategory", diagnostics, record_index=record_index, identifier=identifier) or ""
    content_type = _optional_string(record, "contentType", diagnostics, record_index=record_index, identifier=identifier)
    publication_status = _optional_string(record, "status", diagnostics, record_index=record_index, identifier=identifier)
    updated_on = _optional_string(record, "lastUpdatedOn", diagnostics, record_index=record_index, identifier=identifier)

    presentation_metadata: dict[str, Any] = {}
    for source_name, target_name in (
        ("duration", "raw_duration"),
        ("averageRating", "raw_average_rating"),
        ("thumbnail", "thumbnail"),
        ("appIcon", "app_icon"),
        ("isRejected", "is_rejected"),
    ):
        if source_name in record and record[source_name] is not None:
            presentation_metadata[target_name] = record[source_name]

    competency_name = "; ".join(competency_names) or None
    topic = competency_names[0] if competency_names else category
    document = CourseDocumentPayload(
        course_id=identifier,
        group_id=identifier,
        title=title,
        description=_description(subtitle, instructions),
        tags=tags,
        instructor="",
        language=languages[0] if languages else "",
        available_languages=languages,
        category=category,
        content_type=content_type,
        publication_status=publication_status,
        topic=topic,
        competency_name=competency_name,
        levels=levels,
        updated_on=updated_on,
        duration_minutes=None,
        popularity_score=0.0,
        recency_score=0.0,
        active=True,
        searchable_metadata=competency_names,
        metadata={"sphere_presentation": presentation_metadata},
    )
    return document, diagnostics


def convert_sphere_catalogue_response(payload: object) -> SphereCatalogueConversion:
    diagnostics: list[SphereAdapterDiagnostic] = []
    if not isinstance(payload, Mapping):
        return SphereCatalogueConversion(
            diagnostics=[
                SphereAdapterDiagnostic(
                    severity="error", code="invalid_response_type", message="Sphere response must be an object"
                )
            ]
        )
    result = payload.get("result")
    if not isinstance(result, Mapping):
        return SphereCatalogueConversion(
            diagnostics=[
                SphereAdapterDiagnostic(
                    severity="error", code="missing_result", message="Sphere response.result must be an object"
                )
            ]
        )
    content = result.get("content", [])
    if not isinstance(content, list):
        return SphereCatalogueConversion(
            diagnostics=[
                SphereAdapterDiagnostic(
                    severity="error", code="invalid_content", message="Sphere result.content must be an array"
                )
            ],
            facets_present="facets" in result,
        )

    documents: list[CourseDocumentPayload] = []
    for index, record in enumerate(content):
        document, record_diagnostics = convert_sphere_record(record, index)
        diagnostics.extend(record_diagnostics)
        if document is not None:
            documents.append(document)

    source_count = result.get("count")
    if not isinstance(source_count, int) or isinstance(source_count, bool):
        if source_count is not None:
            diagnostics.append(
                SphereAdapterDiagnostic(
                    severity="warning",
                    code="invalid_source_count",
                    message="Ignored non-integer result.count",
                    field="result.count",
                )
            )
        source_count = None
    return SphereCatalogueConversion(
        documents=documents,
        diagnostics=diagnostics,
        source_count=source_count,
        source_content_length=len(content),
        facets_present="facets" in result,
    )
