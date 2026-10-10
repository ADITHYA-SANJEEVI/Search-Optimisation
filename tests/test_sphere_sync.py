import httpx
import pytest

from app.integrations.sphere_sync import SpherePublicClient, SyncFailure, sync_catalogue
from app.search.backend import InMemorySearchBackend
from app.search.encoder import SemanticEncoder


def record(id, **changes):
    return {"identifier": id, "name": "Pregnancy nutrition", "primaryCategory": "Course", "status": "Live", **changes}


class Source:
    endpoint = "https://invalid.example/publicContent/v1/search"
    def __init__(self, records):
        self.records = records
        self.calls = []
    def page(self, limit, offset):
        self.calls.append((limit, offset))
        return {"result": {"count": len(self.records), "content": self.records[offset:offset + limit]}}


@pytest.fixture()
def backend():
    return InMemorySearchBackend(SemanticEncoder())


@pytest.mark.parametrize("count,pages", [(0, 1), (3, 2), (4, 3)])
def test_all_pages_partial_exact_boundary_zero(backend, count, pages):
    source = Source([record(f"do_{i}") for i in range(count)])
    report = sync_catalogue(source, backend, page_size=2)
    assert report.pages == pages
    assert report.source_records_observed == report.accepted == report.index_document_count == count
    assert source.calls == [(2, i * 2) for i in range(pages)]
    assert report.failures == []


def test_duplicates_optional_malformed_and_exact_identity(backend):
    source = Source([record(" Exact ID "), record(" Exact ID "), {"name": "missing ID"}])
    report = sync_catalogue(source, backend, page_size=2)
    assert (report.source_records_observed, report.accepted, report.rejected, report.duplicates) == (3, 1, 1, 1)
    doc = backend.all_documents()[0]
    assert doc.course_id == " Exact ID "
    assert doc.language == "" and doc.duration_minutes is None


def test_full_repeat_incremental_change_and_removed_source(backend):
    source = Source([record("do_a"), record("do_b")])
    first = sync_catalogue(source, backend)
    assert first.upserted == 2
    assert sync_catalogue(source, backend).index_document_count == 2
    same = sync_catalogue(source, backend, mode="incremental")
    assert (same.upserted, same.unchanged) == (0, 2)
    source.records = [record("do_a", name="Updated title", lastUpdatedOn="2026-10-07T00:00:00Z")]
    changed = sync_catalogue(source, backend, mode="incremental")
    assert (changed.upserted, changed.deleted, changed.index_document_count) == (1, 1, 1)
    assert backend.all_documents()[0].title == "Updated title"


@pytest.mark.parametrize("payload", [{}, {"result": {"content": {}}},
    {"result": {"content": [], "count": 3}}, {"result": {"content": [], "count": "0"}},
    {"result": {"content": [record("a", status="Draft")]}},
    {"result": {"content": [record("a"), record("a", name="conflict")]}}])
def test_malformed_source_fails_before_indexing(backend, payload):
    source = Source([])
    source.page = lambda *args: payload
    with pytest.raises(SyncFailure) as error:
        sync_catalogue(source, backend)
    assert error.value.report.failures
    assert backend.document_count() == 0


def test_repeated_page_and_source_failure(backend):
    source = Source([record("a"), record("b")])
    source.page = lambda *args: {"result": {"content": source.records}}
    with pytest.raises(SyncFailure, match="repeated a page"):
        sync_catalogue(source, backend, page_size=2)
    def fail(*args):
        raise httpx.ConnectError("secret upstream details")
    source.page = fail
    with pytest.raises(SyncFailure) as error:
        sync_catalogue(source, backend)
    assert error.value.report.failures == ["ConnectError"]


def test_index_failure_and_invalid_date(backend, monkeypatch):
    rejected = sync_catalogue(Source([record("bad", lastUpdatedOn="not a date")]), backend)
    assert rejected.rejected == 1 and rejected.accepted == 0
    def fail(*args):
        raise RuntimeError("index failed")
    monkeypatch.setattr(backend, "bulk_upsert", fail)
    with pytest.raises(SyncFailure) as error:
        sync_catalogue(Source([record("a")]), backend)
    assert error.value.report.failures == ["RuntimeError"]


def test_http_request_filters_pagination_and_size_limit():
    calls = []
    def handle(request):
        import json
        calls.append(json.loads(request.content))
        return httpx.Response(200, json={"result": {"content": [], "count": 0}})
    client = httpx.Client(transport=httpx.MockTransport(handle))
    source = SpherePublicClient(Source.endpoint, client=client)
    source.page(100, 200)
    assert calls == [{"request": {"filters": {"primaryCategory": ["Course"], "status": ["Live"]}, "limit": 100, "offset": 200}}]
    source.max_response_bytes = 1
    with pytest.raises(ValueError, match="byte limit"):
        source.page(1, 0)
