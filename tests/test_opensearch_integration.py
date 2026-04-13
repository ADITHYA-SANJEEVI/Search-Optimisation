from __future__ import annotations

import os

import pytest

from app.search.opensearch_validation import run_opensearch_smoke_validation


@pytest.mark.skipif(
    os.getenv("RUN_OPENSEARCH_INTEGRATION", "0") != "1",
    reason="Set RUN_OPENSEARCH_INTEGRATION=1 with a running local OpenSearch node to execute.",
)
def test_opensearch_smoke_validation() -> None:
    report = run_opensearch_smoke_validation()
    assert report["backend"] == "OpenSearchBackedSearchBackend"
    assert report["search_top_group_id"] is not None
    assert report["api_search_status_code"] == 200
    assert report["api_suggest_status_code"] == 200
