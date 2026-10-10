from __future__ import annotations

import json
from pathlib import Path

from app.integrations.sphere_catalog import convert_sphere_catalogue_response, convert_sphere_record
from app.schemas.search import SearchRequest


FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_catalogue_conversion_preserves_canonical_fields_and_raw_values() -> None:
    conversion = convert_sphere_catalogue_response(_fixture("sphere_populated.synthetic.json"))

    assert conversion.source_count == 7
    assert conversion.source_content_length == 2
    assert conversion.facets_present is False
    assert len(conversion.documents) == 2
    document = conversion.documents[0]
    assert document.course_id == "sphere-course-001"
    assert document.group_id == "sphere-course-001"
    assert document.title == "Neonatal Stabilization Essentials"
    assert document.description == "Safe initial care for newborns"
    assert document.language == "English"
    assert document.available_languages == ["English", "Hindi"]
    assert document.competency_name == "Newborn stabilization"
    assert document.levels == ["Foundational"]
    assert document.content_type == "Course"
    assert document.publication_status == "Live"
    assert document.duration_minutes is None
    assert document.popularity_score == 0.0
    assert document.metadata["sphere_presentation"]["raw_duration"] == "1800"
    assert document.metadata["sphere_presentation"]["raw_average_rating"] == 4.25
    assert document.metadata["sphere_presentation"]["is_rejected"] is True
    assert document.active is True


def test_catalogue_conversion_reports_unmappable_and_malformed_records() -> None:
    missing_identifier, errors = convert_sphere_record({"name": "No identity"}, 3)
    assert missing_identifier is None
    assert {diagnostic.code for diagnostic in errors} == {"missing_identifier"}

    document, warnings = convert_sphere_record(
        {
            "identifier": "course-malformed-competency",
            "name": "Still indexable",
            "language": "English",
            "keywords": "not-an-array",
            "competencies_v1": "{broken-json",
        },
        4,
    )
    assert document is not None
    assert document.available_languages == ["English"]
    assert document.competency_name is None
    assert {diagnostic.code for diagnostic in warnings} == {
        "invalid_optional_type",
        "malformed_competency_json",
    }


def test_canonical_identifier_is_not_normalized() -> None:
    document, diagnostics = convert_sphere_record(
        {"identifier": "  Sphere:Course/Exact-ID  ", "name": "Exact identity"}
    )

    assert diagnostics == []
    assert document is not None
    assert document.course_id == "  Sphere:Course/Exact-ID  "
    assert document.group_id == "  Sphere:Course/Exact-ID  "


def test_empty_response_and_optional_facets_are_preserved() -> None:
    conversion = convert_sphere_catalogue_response(_fixture("sphere_empty.synthetic.json"))

    assert conversion.documents == []
    assert conversion.source_count == 0
    assert conversion.source_content_length == 0
    assert conversion.facets_present is True
    assert conversion.diagnostics == []


def test_converted_catalogue_can_be_indexed_and_retrieved(container) -> None:
    conversion = convert_sphere_catalogue_response(_fixture("sphere_populated.synthetic.json"))
    container.index_service.bulk_index(conversion.documents)

    response = container.search_service.search(
        SearchRequest(
            query="neonatal stabilization",
            filters={
                "categories": ["Course"],
                "content_types": ["Course"],
                "publication_statuses": ["Live"],
            },
            page_size=1,
        )
    )

    assert response.results[0].course_id == "sphere-course-001"
    assert response.pagination.page_size == 1
    assert conversion.source_count != len(response.results)


def test_presentation_metadata_does_not_influence_retrieval(container) -> None:
    conversion = convert_sphere_catalogue_response(_fixture("sphere_populated.synthetic.json"))
    container.index_service.bulk_index(conversion.documents)

    response = container.search_service.search(SearchRequest(query="display only catalog token zzq"))

    assert all(result.course_id != "sphere-course-001" for result in response.results)
