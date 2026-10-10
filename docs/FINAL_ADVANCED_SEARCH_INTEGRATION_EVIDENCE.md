# Final status

COMPLETE WITH EXTERNAL DEPLOYMENT BLOCKERS.

Repository-owned implementation and local acceptance are complete. No production/Kong deployment or upstream proxy merge is claimed.

# Repository / branch

`C:\Users\adith\OneDrive\Desktop\aastrika`; `feature/sphere-contract-adapter-local-20260930-1652`. Starting HEAD: `b2ba79fb4b8a9b1185442753100ae8e75948e6a3`. Starting working tree was dirty, with catalogue/ranking enhancements mixed with earlier presentation, branding, browser-voice, and launcher edits. Initial inspection mapping is in `INTEGRATION_GAPS.md`.

# Final commit SHA

No final commit. HEAD remains `b2ba79fb4b8a9b1185442753100ae8e75948e6a3`. The changes depend on prior edits in shared files; an atomic stage of the entire dirty tree would include unrelated work. Existing changes were preserved, nothing staged or discarded, no history rewritten, no remote push.

# Architecture implemented

Python/FastAPI transport, existing QueryProcessor + PRISM ranking, explicit persistent OpenSearch catalogue, full snapshot scan/reload for scoring. Node proxy owns full-record hydration. No Java/LERN change and no ranking-engine replacement. The existing `/api/v1/search` full-record demo contract is separate from the new Sphere endpoint.

# API contract

`POST /v1/search`, JSON. Exact request/response pair exercised on the real index:

```json
{"query":"pregnancy","filters":{},"limit":2,"offset":2}
```

```json
{"ids":["do_1140040324179148801162","do_1143718632876851201351"],"total":36,"corrected_query":"fever in pregnancy"}
```

Mandatory response fields: `ids`, `total`; optional engine-supplied `corrected_query`. No full records, scores, internal documents, or debug fields. Query defaults to empty (max 240 characters); strict limit 1..100/default 10; strict offset 0..1,000,000/default 0. Unknown fields/invalid filters return 422; index unavailability returns 503. Supported filters and adapter field mapping are in `SPHERE_API_CONTRACT.md`.

# Query vs browse semantics

A nonblank query uses complete-population PRISM relevance, score descending and exact course ID as the tie breaker. No caller sort can override it. Browse restricts to active Live Courses and uses parsed `lastUpdatedOn` descending, missing dates last, exact course-ID ties. The real browse first 100 IDs matched an independently sorted OpenSearch query. The IDs population is unique course IDs, without the legacy demo's group collapse.

# Pagination

Filters and ordering precede offset/limit. Matching total is unchanged across pages, including offset at/beyond total. Unit/API/real-index/live tests explicitly exercised page changes and stable repeated requests. The Sphere request translator forwards nested or outer limit/offset and rejects conflicts.

# Sync

`scripts/sync_sphere.py --mode full|incremental`. Public filters are Live + Course; both limit and offset are sent. Traversal continues through all pages and validates exhaustion/count consistency. Records use the existing adapter and exact original IDs. Repeated full runs are upsert-safe. Incremental mode still pages the entire catalogue and compares raw content SHA-256 fingerprints in persisted metadata; it is not an upstream delta feed. Complete rejection-free traversals prune absent source-owned records. Rejections suppress pruning. Source failures precede writes; index failures are reported and bulk writes are not atomic.

Full sync began **7 October 2026, 19:24:41 IST** (13:54:41 UTC): page size 100, **7 pages, 620 observed, 620 accepted, 0 rejected, 0 duplicate IDs, 620 upserted, 620 index documents, 0 failures**. Incremental sync began **19:28:21 IST**: **7 pages, 620 observed/accepted, 620 unchanged, 0 upserts, 0 rejected, 620 index documents, 0 failures**. Counts were fetched live; 620 is never a source-count constant. Two incompatible optional `competencies_v1` values were diagnosed/ignored in both reports; they did not reject courses.

# OpenSearch

Local Docker OpenSearch **2.19.1** runs at loopback port 9200. The `sphere-courses-v1` index contains 620 persisted documents, one shard, zero replicas. Its index health is green; overall local cluster health is yellow. Explicit strict mapping includes canonical keyword IDs, dates, typed fields with numeric coercion disabled, and non-searchable presentation metadata. Invalid dynamic fields and numeric strings were rejected against a real temporary index. Index recreation is not automatic for incompatible mappings: configure a new index and full-sync it. Cache reload scans all documents rather than a fixed 10,000-result window. Writes persist before the local cache changes; bulk failure reloads persisted state. Readiness returns 503 for unavailable/missing/count-mismatched or empty index states; liveness does no backend I/O. Configured OpenSearch startup failure no longer silently falls back to memory.

# UI proxy integration

**Exact integration patch/handoff only, not a merge into the actual proxy.** Inspected upstream `src/publicApi_v8/publicSearch.ts` at `Sphere/sunbird-cb-uiproxy`, `cbrelease-4.0.1`, commit `d85cc8ca5f898919a61bae5dd0823d08ad305d50`. `integration/ui-proxy/publicSearch.patch` applies cleanly to that snapshot and adds the exact locally tested companion.

Flag defaults off; applicable query requests forward filters/limit/offset. Ranked IDs are hydrated through the unchanged public search API by identifier and reordered without date sorting. Missing/extra records are handled deterministically. Failures or unsupported UI filters retain the original path, without recursion. Browse remains on the original proxy path. Existing `!competency` visibility is retained; the live three-ID page returned two visible records and omitted `do_1143718632876851201351`, keeping matching total 36. Upstream full TypeScript/app build has not been executed from this checkout.

# Kong status

**CONFIG READY / EXTERNAL ENVIRONMENT BLOCKED.** `integration/kong/advanced-search.yml` maps POST `/apis/proxies/v8/advanced-search/v1/search` to internal `/v1/search`, with path stripping and bounded timeouts. No Kong credentials/configuration access were available. No Kong deployment, gateway smoke test, or production onboarding is claimed. Environment owner must set the actual host/port and existing gateway auth policy.

# Search quality

Existing 272-case data/expected answers were retained. **250/252 positive top-1 (99.21%), 252/252 positive top-3 (100%), 20/20 negative no-result cases**. Overall and per-tag recorded results match the starting benchmark: no measured regression. Six named typo/acronym/sentence-language/difficulty/competency/compact-query cases also passed through the IDs boundary. Typo 12/12, acronym 58/58, NLP 12/12, language preference 6/6, competency 6/6; level-query top-1 remains 5/6 (83.33%), top-3 6/6. The original 85% level top-1 aspiration is not met; no threshold or expected answer was changed. The 30 aspirational metrics are not all separately measured.

# Test results

Environment for Python acceptance: `$env:RUN_OPENSEARCH_INTEGRATION='1'`; local real OpenSearch available.

| Exact command | Passed | Failed | Errors | Skipped | Xfailed |
| --- | ---: | ---: | ---: | ---: | ---: |
| `.\.venv\Scripts\python.exe -m pytest -q -rA --junitxml=artifacts/final_pytest.xml` | 90 | 0 | 0 | 0 | 0 |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_advanced_search.py::test_backend_failure_readiness_and_liveness tests/test_opensearch_contract.py --junitxml=artifacts/final_health_pytest.xml` | 2 | 0 | 0 | 0 | 0 |
| `node --experimental-strip-types --test integration/ui-proxy/advancedSearch.test.mjs` | 7 | 0 | 0 | 0 | 0 |

The focused two-test rerun followed the final health/liveness refinement. The initial baseline was 50 passed, 1 infrastructure-opt-in skip; the integration test was preserved and executed in final acceptance. No xfail or removed-test workaround was used. Plain pytest without the integration flag is not the claimed acceptance run.

Additional successful commands (exit 0; not pytest-style counts):

```powershell
docker compose config --quiet
docker compose up -d opensearch
.\.venv\Scripts\python.exe scripts/sync_sphere.py --mode full --report artifacts/sphere_full_sync_report.json
.\.venv\Scripts\python.exe scripts/sync_sphere.py --mode incremental --report artifacts/sphere_incremental_sync_report.json
.\.venv\Scripts\python.exe scripts/run_benchmark.py
.\.venv\Scripts\python.exe scripts/validate_sphere_live.py
node --experimental-strip-types integration/ui-proxy/liveAcceptance.mjs
.\.venv\Scripts\python.exe -m compileall -q app scripts tests
node --check integration/ui-proxy/advancedSearch.test.mjs
node --check integration/ui-proxy/liveAcceptance.mjs
git apply --check --directory=artifacts/runtime/proxy-patch-check integration/ui-proxy/publicSearch.patch
git diff --check
```

API startup: `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8017`, with SEARCH_BACKEND=opensearch, OPENSEARCH_INDEX=sphere-courses-v1, BOOTSTRAP_SAMPLE_DATA=false. Latest local startup was verified after restart. No lint/typechecker is configured in this Python checkout; no invented lint acceptance is claimed. Docker API image startup/build was not measured; native API + Docker OpenSearch were.

# Real-data validation / end-to-end evidence

Source: `https://sphere.aastrika.org/apis/public/v8/publicContent/v1/search` (public read-only POSTs only).

- A: real query -> original IDs -> offset page -> existing public record fetch -> ranked reorder, including deliberate fetch-order reversal in the exact Node helper.
- B: real typo `postpartm hemorhage managment` -> `postpartum hemorrhage management` -> nonempty original IDs.
- C: real browse total 620 -> date-desc IDs independently matched to OpenSearch -> offset page.
- D: advanced failure -> legacy fallback once, flag-off/browse/unsupported-filter behavior proved by local Node contract tests; not the running upstream application.
- E: all seven public pages -> 620 indexed -> index count reconciled; incremental traversal -> zero writes.

Evidence files: `artifacts/sphere_full_sync_report.json`, `sphere_incremental_sync_report.json`, `sphere_live_acceptance.json`, `proxy_live_acceptance.json`, `benchmark_report.json`, `final_pytest.xml`, `final_health_pytest.xml`, `final_checks.json`.

# Security/configuration checks

`.env` remains ignored and untracked; `.env.example` uses a placeholder API key. Raw network source capture is confined to ignored `artifacts/runtime/`. No source authentication headers/cookies/tokens were needed, printed, or committed. Synthetic-fixture authentication hygiene tests passed. New sync errors use safe fixed diagnostics/type names; API 503s do not expose index documents or dependency details. URLs come from trusted environment configuration, never search request input. Upstream timeouts/page/response-size limits are bounded. Local OpenSearch security-disabled configuration is explicitly development-only and bound to loopback. Normal gateway/service auth policy remains the environment owner's responsibility.

# Files changed

All workspace changes relative to starting HEAD are listed below, including preserved preexisting files. Shared files contain earlier user changes; the list does not imply this pass authored every edit.

- `.env.example`
- `.gitignore`
- `README.md`
- `app/__init__.py`
- `app/api/advanced_search.py`
- `app/api/health.py`
- `app/api/search.py`
- `app/core/config.py`
- `app/integrations/__init__.py`
- `app/integrations/sphere_catalog.py`
- `app/integrations/sphere_request.py`
- `app/integrations/sphere_sync.py`
- `app/main.py`
- `app/models/course.py`
- `app/ranking/reranker.py`
- `app/schemas/indexing.py`
- `app/schemas/search.py`
- `app/schemas/sphere.py`
- `app/search/backend.py`
- `app/search/encoder.py`
- `app/search/opensearch_backend.py`
- `app/search/opensearch_validation.py`
- `app/services/bootstrap.py`
- `app/services/search_service.py`
- `app/static/debug.html`
- `app/static/demo.html`
- `app/utils/dates.py`
- `artifacts/benchmark_report.json`
- `artifacts/final_checks.json`
- `artifacts/final_health_pytest.xml`
- `artifacts/final_pytest.xml`
- `artifacts/proxy_live_acceptance.json`
- `artifacts/sphere_full_sync_report.json`
- `artifacts/sphere_incremental_sync_report.json`
- `artifacts/sphere_live_acceptance.json`
- `docker-compose.yml`
- `docs/FINAL_ADVANCED_SEARCH_INTEGRATION_EVIDENCE.md`
- `docs/INTEGRATION_GAPS.md`
- `docs/PRINCE_HANDOFF.md`
- `docs/SPHERE_API_CONTRACT.md`
- `docs/aastrika_prism_rank.md`
- `docs/api_contract.md`
- `docs/architecture.md`
- `docs/current_status.md`
- `docs/deployment.md`
- `docs/java_integration.md`
- `docs/presentation_briefing.md`
- `docs/search_test_cases.md`
- `docs/testing_and_evaluation.md`
- `integration/kong/advanced-search.yml`
- `integration/ui-proxy/advancedSearch.test.mjs`
- `integration/ui-proxy/advancedSearch.ts`
- `integration/ui-proxy/liveAcceptance.mjs`
- `integration/ui-proxy/publicSearch.patch`
- `launch.ps1`
- `scripts/run_local.ps1`
- `scripts/sync_sphere.py`
- `scripts/validate_sphere_live.py`
- `tests/fixtures/sphere_empty.synthetic.json`
- `tests/fixtures/sphere_populated.synthetic.json`
- `tests/test_advanced_search.py`
- `tests/test_opensearch_contract.py`
- `tests/test_prism_rank.py`
- `tests/test_search_flow.py`
- `tests/test_sphere_catalog_adapter.py`
- `tests/test_sphere_contract_hygiene.py`
- `tests/test_sphere_hard_filters.py`
- `tests/test_sphere_request_adapter.py`
- `tests/test_sphere_sync.py`

# Remaining external actions

Review/merge/build the exact patch in the actual Node proxy repository; onboard the Kong route/service with environment policies; deploy the API/index; schedule sync and coordinate snapshot refresh; execute platform traffic acceptance. No remote push was performed.

# Limitations

Ranking remains a complete in-process snapshot, requiring API restart after an external CLI sync. Fingerprint mode scans all source pages and local adapter upgrades need a full sync. The upstream API has no snapshot/delta guarantee; inconsistent counts/repeated pages are detected, but simultaneous same-count catalogue changes cannot be fully excluded. Bulk indexing is not transactional. The preserved adapter ignored two incompatible optional competency values, without inventing fields. Optional duration/ratings do not become inferred filter/ranking signals. Legacy proxy competency exclusion can shorten hydrated pages; its facets are from the public page fetch, not a new global aggregation. Source-record filtering/inference and benchmark weights remain tuned to the checked-in corpus; live query `pregnancy` was corrected to `fever in pregnancy`, so broad real-catalogue relevance quality is not established by the sample metrics. No production traffic, SLA, scheduler, managed cluster, full upstream build, or Kong/platform acceptance is claimed.
