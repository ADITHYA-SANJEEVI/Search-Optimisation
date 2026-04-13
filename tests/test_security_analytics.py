from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.schemas.search import SearchRequest
from app.services.bootstrap import build_container


def test_auth_rejects_missing_key(workspace_tmp_path) -> None:
    previous_auth = settings.auth_enabled
    previous_db = settings.analytics_db_path
    settings.auth_enabled = True
    settings.analytics_db_path = str(workspace_tmp_path / "analytics.db")
    try:
        app.state.container = build_container()
        with TestClient(app) as client:
            response = client.post("/api/v1/search", json={"query": "pph assessment"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "auth_required"
    finally:
        settings.auth_enabled = previous_auth
        settings.analytics_db_path = previous_db


def test_auth_accepts_valid_key(workspace_tmp_path) -> None:
    previous_auth = settings.auth_enabled
    previous_db = settings.analytics_db_path
    settings.auth_enabled = True
    settings.analytics_db_path = str(workspace_tmp_path / "analytics.db")
    try:
        app.state.container = build_container()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/search",
                json={"query": "pph assessment"},
                headers={settings.api_key_header_name: next(iter(settings.api_keys))},
            )
        assert response.status_code == 200
        assert response.json()["results"]
    finally:
        settings.auth_enabled = previous_auth
        settings.analytics_db_path = previous_db


def test_rate_limit_blocks_excess_requests(workspace_tmp_path) -> None:
    previous_rate = settings.rate_limit_enabled
    previous_limit = settings.rate_limit_requests
    previous_window = settings.rate_limit_window_seconds
    previous_db = settings.analytics_db_path
    settings.rate_limit_enabled = True
    settings.rate_limit_requests = 2
    settings.rate_limit_window_seconds = 60
    settings.analytics_db_path = str(workspace_tmp_path / "analytics.db")
    try:
        app.state.container = build_container()
        with TestClient(app) as client:
            first = client.post("/api/v1/search", json={"query": "pph assessment"})
            second = client.post("/api/v1/search", json={"query": "pph assessment"})
            third = client.post("/api/v1/search", json={"query": "pph assessment"})
        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
        assert third.json()["error"]["code"] == "rate_limit_exceeded"
    finally:
        settings.rate_limit_enabled = previous_rate
        settings.rate_limit_requests = previous_limit
        settings.rate_limit_window_seconds = previous_window
        settings.analytics_db_path = previous_db


def test_audio_request_size_limit_is_enforced(workspace_tmp_path) -> None:
    previous_max_audio = settings.max_audio_upload_bytes
    previous_db = settings.analytics_db_path
    settings.max_audio_upload_bytes = 8
    settings.analytics_db_path = str(workspace_tmp_path / "analytics.db")
    try:
        app.state.container = build_container()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/search/voice",
                files={"file": ("big.wav", b"0123456789", "audio/wav")},
            )
        assert response.status_code == 413
        assert response.json()["error"]["code"] in {"request_too_large", "audio_too_large"}
    finally:
        settings.max_audio_upload_bytes = previous_max_audio
        settings.analytics_db_path = previous_db


def test_analytics_are_persisted_and_non_fatal() -> None:
    previous_db = settings.analytics_db_path
    temp_dir = Path("artifacts") / "test_tmp" / f"analytics-persist-{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    db_path = temp_dir / "analytics.db"
    settings.analytics_db_path = str(db_path)
    try:
        tracked = build_container()
        response = tracked.search_service.search(SearchRequest(query="pph assessment"))
        assert response.results
        assert tracked.analytics.store is not None
        assert tracked.analytics.store.recent_search_events(limit=5)
    finally:
        settings.analytics_db_path = previous_db
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_analytics_storage_failure_does_not_break_search(container) -> None:
    class BrokenStore:
        def record_search_event(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("db down")

        def record_correction_event(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("db down")

        def health_details(self) -> dict[str, object]:
            return {"status": "degraded", "details": {"reason": "db down"}}

    container.analytics.store = BrokenStore()  # type: ignore[assignment]
    response = container.search_service.search(SearchRequest(query="pph assessment"))
    assert response.results
