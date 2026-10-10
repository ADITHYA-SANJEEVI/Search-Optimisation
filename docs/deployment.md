# Local integration runbook

Run from the repository root with Docker Desktop started and Python dependencies installed in `.venv`. OpenSearch security is disabled solely for local development; Docker publishes it on loopback and persists data in a named volume. No production deployment is represented here.

```powershell
docker compose config --quiet
docker compose up -d opensearch
$env:OPENSEARCH_INDEX='sphere-courses-v1'
$env:SPHERE_PUBLIC_SEARCH_URL='https://sphere.aastrika.org/apis/public/v8/publicContent/v1/search'
.\.venv\Scripts\python.exe scripts/sync_sphere.py --mode full --report artifacts/sphere_full_sync_report.json
.\.venv\Scripts\python.exe scripts/sync_sphere.py --mode incremental --report artifacts/sphere_incremental_sync_report.json
$env:SEARCH_BACKEND='opensearch'
$env:BOOTSTRAP_SAMPLE_DATA='false'
$env:ENABLE_DEBUG_PAYLOADS='false'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8017
```

In a second terminal:

```powershell
$env:SPHERE_PUBLIC_SEARCH_URL='https://sphere.aastrika.org/apis/public/v8/publicContent/v1/search'
.\.venv\Scripts\python.exe scripts/validate_sphere_live.py
node --experimental-strip-types integration/ui-proxy/liveAcceptance.mjs
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

The host settings module reads process environment, not `.env` automatically. `.env.example` contains placeholders and safe local integration values. Docker's API service reads it and overrides the internal OpenSearch host to `opensearch`. After a host-side sync, `docker compose up -d --build search-opt` is the container API alternative; container startup was not part of the measured API smoke run. Keep API/index names aligned. Existing incompatible indexes fail initialization: configure a new index and full-sync it rather than deleting data blindly.

Sync pages are bounded to 1..100 records with a 1,000-page guard, 20-second default HTTP timeout, and 16 MiB response limit. Report counts include observed records, accepted unique records, rejected records, duplicate observations, unchanged/upserted/deleted records, index count, diagnostics, and failures. A partial page terminates traversal, with one empty terminal page at an exact boundary. Reported source counts are checked for consistency; repeats, truncation, malformed envelopes, dependency errors, and conflicting duplicate IDs fail explicitly. Source traversal completes before any writes. Bulk writes are upserts, not a multi-document transaction; index failures can partially persist and require a rerun.

Stop or restart the API after external sync to refresh its local snapshot. Full mode rewrites all accepted records; incremental mode compares the complete raw source fingerprint, not just a timestamp. Source-owned absent IDs are reconciled in either mode only after a complete rejection-free traversal. Zero records is valid for sync; the service remains warming until populated. There is no production scheduler configured.

`launch.ps1` remains the existing sample presentation launcher. It explicitly loads sample data and must not be used against the real catalogue index. Use the commands above for Sphere integration. Stop the measured API using its recorded managed process in `artifacts/runtime/closure-api.pid` after verifying the process; stop local OpenSearch with `docker compose stop opensearch` when finished.
