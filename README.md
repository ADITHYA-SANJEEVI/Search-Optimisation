# Aastrika Sphere

Aastrika Sphere is a compact intelligent search backend for healthcare course discovery. The surface area is intentionally small: one FastAPI service, one lightweight verification UI, and one local in-memory backend for development. The interesting work is in the retrieval pipeline itself: query normalization, typo repair, transliteration support, hybrid ranking, phonetic rescue, and practical optimization choices for noisy real-world course search.

It should be read as a focused search systems project, not as a massive platform.

## Why This Is Interesting

- It handles exact queries, noisy queries, acronym-heavy queries, missing-space queries, romanized Hindi, and code-mixed inputs in one retrieval flow.
- It combines lexical BM25-style matching, fuzzy repair, phonetic matching, and semantic rescue behind a clean REST API.
- It keeps the implementation small enough to inspect end-to-end while still exposing indexing, suggestions, health checks, analytics hooks, and voice-search seams.
- It is designed to be called from a Java service over HTTP without coupling runtimes or storage layers.

## Retrieval Pipeline

1. Normalize the query: Unicode cleanup, casing, punctuation removal, repeated-letter cleanup, filler-word stripping.
2. Repair the query: token-level typo correction, title-level fuzzy repair, compact-title recovery for missing spaces, transliteration expansion.
3. Infer intent: language preference, difficulty, topic hints, code-mixed detection, query summarization.
4. Retrieve candidates: title/body BM25-style scoring, fuzzy similarity, phonetic overlap, semantic similarity.
5. Rerank results: weighted hybrid score with phrase overrides, language boost, popularity and recency hooks, confidence estimation.
6. Enrich the response: explanations, grouped variants, facets, alternate queries, no-result guidance, debug payloads.

This is implemented primarily in [app/search/query_processor.py](app/search/query_processor.py), [app/search/backend.py](app/search/backend.py), and [app/services/search_service.py](app/services/search_service.py).

## Benchmark Snapshot

From [`artifacts/benchmark_report.json`](artifacts/benchmark_report.json):

- `top1`: `250 / 252` -> `99.2%`
- `top3`: `252 / 252` -> `100%`
- negative-query pass rate: `20 / 20` -> `100%`

The evaluation set includes exact-title, acronym, typo, no-space, romanized Hindi, Hindi-script, code-mixed, voice-style, and other generated NLP variants. For a small domain-specific search system, that is the core result.

Current local test run:

- `27 passed, 1 skipped`

## Demo UI

The repo includes a lightweight verification surface at `/demo`. It is not the product. It exists to make the retrieval behavior easy to inspect.

![Search home](docs/images/demo-home.png)

![Filtered results](docs/images/demo-results.png)

![Typo-tolerant retrieval](docs/images/demo-repair.png)

Screenshots can be regenerated locally with [`scripts/capture_demo_screenshots.ps1`](scripts/capture_demo_screenshots.ps1).

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
```

Local endpoints:

- API root: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Demo UI: `http://localhost:8000/demo`
- Debug UI: `http://localhost:8000/demo/debug`

The default local path uses the in-memory backend and loads [`sample_data/courses.json`](sample_data/courses.json).

## API Surface

- `POST /api/v1/search`
- `GET /api/v1/suggest`
- `POST /api/v1/search/voice`
- `POST /api/v1/index/bulk`
- `POST /api/v1/index/update`
- `POST /api/v1/index/delete`
- `POST /api/v1/index/reindex`
- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/live`

The API contract is documented in [docs/api_contract.md](docs/api_contract.md).

## Technical Notes

- Default backend: in-memory search backend behind a `SearchBackend` abstraction.
- Optional backend path: OpenSearch adapter validation through Docker.
- Semantic path: sentence-transformers when available, with local fallback behavior.
- Voice path: mock STT by default, `faster-whisper` integration seam available.
- Operational controls: auth middleware, rate limiting, structured error envelopes, analytics logging.

This is a practical prototype with real retrieval logic, not a claim of web-scale search or fully validated production readiness.

## Project Layout

- `app/api/` REST routes and request wiring
- `app/search/` normalization, repair, retrieval, encoding
- `app/ranking/` hybrid scoring and confidence
- `app/suggest/` grouped autocomplete suggestions
- `app/voice/` speech-to-text adapter seam
- `app/services/` orchestration and response assembly
- `tests/` search, indexing, normalization, failure-mode, suggestion, and integration tests
- `docs/` architecture, deployment, API, evaluation, and Java integration notes

## Optional OpenSearch Validation

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_opensearch.ps1
python .\scripts\opensearch_smoke_test.py
powershell -ExecutionPolicy Bypass -File .\scripts\stop_opensearch.ps1
```

OpenSearch is optional. Local demo and development do not require Docker.

## Additional Documentation

- [docs/architecture.md](docs/architecture.md)
- [docs/search_pipeline.md](docs/search_pipeline.md)
- [docs/testing_and_evaluation.md](docs/testing_and_evaluation.md)
- [docs/java_integration.md](docs/java_integration.md)
- [docs/current_status.md](docs/current_status.md)
