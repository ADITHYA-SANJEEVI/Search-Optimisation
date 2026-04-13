from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.main import app
from app.services.bootstrap import build_container


@pytest.fixture()
def workspace_tmp_path():
    artifacts_dir = ROOT / "artifacts" / "test_tmp"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="pytest-work-", dir=artifacts_dir))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def container(workspace_tmp_path):
    previous_db = settings.analytics_db_path
    previous_auth = settings.auth_enabled
    previous_rate = settings.rate_limit_enabled
    settings.analytics_db_path = str(workspace_tmp_path / "analytics.db")
    settings.auth_enabled = False
    settings.rate_limit_enabled = False
    try:
        return build_container()
    finally:
        settings.analytics_db_path = previous_db
        settings.auth_enabled = previous_auth
        settings.rate_limit_enabled = previous_rate


@pytest.fixture()
def client(workspace_tmp_path):
    previous_db = settings.analytics_db_path
    previous_auth = settings.auth_enabled
    previous_rate = settings.rate_limit_enabled
    settings.analytics_db_path = str(workspace_tmp_path / "analytics.db")
    settings.auth_enabled = False
    settings.rate_limit_enabled = False
    try:
        app.state.container = build_container()
        with TestClient(app) as test_client:
            yield test_client
    finally:
        settings.analytics_db_path = previous_db
        settings.auth_enabled = previous_auth
        settings.rate_limit_enabled = previous_rate
