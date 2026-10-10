import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.integrations.sphere_sync import sync_catalogue
from app.services.bootstrap import build_container


def record(identifier, **changes):
    return {"identifier": identifier, "name": "Pregnancy nutrition", "primaryCategory": "Course", "status": "Live", **changes}


class Source:
    endpoint = "https://invalid.example/publicContent/v1/search"
    def __init__(self, records):
        self.records = records
    def page(self, limit, offset):
        return {"result": {"count": len(self.records), "content": self.records[offset:offset + limit]}}


@pytest.mark.skipif(os.getenv("RUN_OPENSEARCH_INTEGRATION") != "1", reason="Requires local OpenSearch")
def test_real_index_sync_restart_search_pagination_mapping_and_readiness(monkeypatch):
    index = "sphere-contract-test-" + uuid.uuid4().hex
    monkeypatch.setattr(settings, "search_backend", "opensearch")
    monkeypatch.setattr(settings, "opensearch_index", index)
    monkeypatch.setattr(settings, "bootstrap_sample_data", False)
    previous = app.state.container
    container = build_container()
    backend = container.backend
    try:
        source = Source([record("do_old", lastUpdatedOn="2025-01-01T00:00:00Z"),
                         record("do_new", name="Pregnancy support", lastUpdatedOn="2026-10-01T00:00:00Z")])
        report = sync_catalogue(source, backend, page_size=1)
        assert (report.pages, report.upserted, report.index_document_count) == (3, 2, 2)
        report = sync_catalogue(source, backend, mode="incremental")
        assert (report.upserted, report.unchanged) == (0, 2)
        reloaded = build_container()
        app.state.container = reloaded
        with TestClient(app) as client:
            assert client.get("/api/v1/ready").status_code == 200
            assert client.post("/v1/search", json={"query": "Pregnancy nutrition", "limit": 1}).json()["ids"] == ["do_old"]
            assert client.post("/v1/search", json={"limit": 1}).json() == {"ids": ["do_new"], "total": 2}
            assert client.post("/v1/search", json={"offset": 1, "limit": 1}).json() == {"ids": ["do_old"], "total": 2}
            with pytest.raises(Exception):
                backend.client.index(index=index, id="bad", body={"course_id": "bad", "unknown": "field"}, refresh=True)
            with pytest.raises(Exception):
                backend.client.index(index=index, id="bad", body={"course_id": "bad", "duration_minutes": "5"}, refresh=True)
            assert backend.client.count(index=index)["count"] == 2
            backend.client.indices.delete(index=index)
            assert client.get("/api/v1/ready").status_code == 503
            assert client.post("/v1/search", json={"query": "pregnancy"}).status_code == 503
            assert client.get("/api/v1/live").status_code == 200
        reloaded.backend.client.close()
    finally:
        if backend.client.indices.exists(index=index):
            backend.client.indices.delete(index=index)
        backend.client.close()
        app.state.container = previous
