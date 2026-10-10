# Testing and evaluation

The 11 October repository freeze runs this acceptance once more, retaining the
7 October evidence below. Current Python output is `artifacts/release_pytest.xml`;
the current summary is [REPOSITORY_FREEZE.md](REPOSITORY_FREEZE.md). The historical
`final_pytest.xml`, focused health report, sync reports, and live acceptance reports
remain intact. No new full public catalogue sync is required for publication.

Final acceptance uses a running local OpenSearch node and explicitly enables infrastructure coverage:

```powershell
docker compose up -d opensearch
# Wait until `docker compose ps` reports OpenSearch healthy.
# Use the sample backend for ordinary tests; opt-in tests create isolated indexes.
$env:SEARCH_BACKEND='inmemory'
$env:BOOTSTRAP_SAMPLE_DATA='true'
$env:AUTH_ENABLED='false'
$env:RATE_LIMIT_ENABLED='false'
$env:SEMANTIC_MODEL_ALLOW_DOWNLOAD='false'
$env:ENABLE_DEBUG_PAYLOADS='true'
$env:RUN_OPENSEARCH_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest -q -rA --junitxml=artifacts/release_pytest.xml
node --experimental-strip-types --test integration/ui-proxy/advancedSearch.test.mjs
.\.venv\Scripts\python.exe scripts/run_benchmark.py
```

Measured: 90 Python tests passed, 0 failed, 0 errors, 0 skipped, 0 xfailed. Node: 7 passed with no failures, skips, or TODOs. The subsequent focused health/index rerun passed 2 tests. JUnit results are checked in `artifacts/`; the historical opt-in integration test remains intact and is actually exercised. Without RUN_OPENSEARCH_INTEGRATION=1 the infrastructure tests are skipped; that default run is not the claimed final acceptance suite.

Tests cover IDs-only shape, original IDs, query relevance over dates, date browse and deterministic ties, matching total, limit/offset and beyond-total pages, strict invalid inputs, supported/unsupported filters, filtered pages, empty results, original quality cases, source pagination/exhaustion/duplicate/malformed records, changed/removal/repeated sync, source/index failures, real OpenSearch persistence/reload/mapping rejection/readiness, and Node flag/fallback/reorder/hydration behavior. Temporary integration indexes are isolated and removed; the real catalogue index is retained.

The historical evaluation data and expected groups were not changed. The 272-case suite retains 250/252 positive top-1, 252/252 positive top-3, and 20/20 negative no-result cases. Per-tag results remain in `artifacts/benchmark_report.json`. The existing level-query top-1 result is 5/6 (83.3%), below the aspirational 85% in the original search-case document; it is a retained limitation, not a newly passing metric. Not all 30 aspirational metrics have a dedicated measurement, so no blanket claim is made for them.

Live read-only scenarios use `scripts/validate_sphere_live.py` and `integration/ui-proxy/liveAcceptance.mjs`; configuration and commands are in [deployment.md](deployment.md). Reports contain counts/IDs, not raw source catalogue/authentication captures. Optional voice still has mock and existing faster-whisper paths; broad real-audio acceptance is outside this integration.
