# QueryCore

QueryCore is a search optimisation system for healthcare course discovery. It is engineered around the core problems that define high-quality retrieval in practice: query normalization, repair under noisy user input, multilingual matching, transliteration-aware search, hybrid ranking, precision control, and recovery-oriented response shaping. The result is a backend that turns difficult, irregular, high-variance search traffic into consistently strong retrieval behavior through disciplined ranking logic and well-chosen optimisation techniques.

## Why This Is Interesting

- It handles exact queries, noisy queries, acronym-heavy queries, missing-space queries, romanized Hindi, and code-mixed inputs inside one retrieval architecture rather than through ad hoc exceptions.
- It combines BM25-style lexical evidence, fuzzy repair, phonetic comparison, and semantic rescue behind a clean REST boundary.
- It exposes indexing, suggestions, health checks, analytics hooks, and voice-search seams inside a single end-to-end search stack.
- It is designed to be consumed by a Java service over HTTP without coupling storage, runtime, or indexing internals.

## System Character

QueryCore stands out because it applies a set of search optimisation techniques with discipline and internal coherence:

- aggressive query cleanup before retrieval
- multiple repair paths for user-input noise
- domain-aware language and transliteration handling
- hybrid evidence accumulation instead of single-score ranking
- rescue logic for difficult queries
- measurable evaluation instead of anecdotal demos

That combination gives the system strong retrieval depth, strong explainability, and strong practical value.

## Course Data Profile

The sample corpus is deliberately rich in the kinds of variation that make search difficult and interesting. Course titles and aliases span maternal health, antenatal care, emergency obstetrics, newborn care, counselling, lactation, referral systems, high-risk pregnancy, postpartum hemorrhage, Kangaroo Mother Care, ENBC, and stage 4 monitoring.

The names themselves are noisy and diverse in exactly the way real search traffic tends to be noisy and diverse:

- full descriptive titles and short labels coexist
- acronyms such as `PPH`, `HRP`, `KMC`, `ENBC`, and `FRU` appear alongside expanded forms
- Hindi script, English titles, and romanized Hindi variants appear in the same search universe
- topic phrasing varies across clinical terms, competency names, and user-facing course names
- spacing, punctuation, casing, transliteration, and word-order variation all matter materially to retrieval quality

That data profile makes QueryCore an optimisation problem in the real sense of the term: ranking quality depends on how well the system reconciles lexical precision, language variation, phonetic closeness, and semantic intent.

## Retrieval Pipeline

1. Normalize the query: Unicode cleanup, casing normalization, punctuation removal, repeated-letter reduction, filler-word stripping, and compact-text handling.
2. Repair the query: token-level typo correction, title-level fuzzy repair, compact-title recovery for missing spaces, and transliteration expansion.
3. Infer intent: language preference, difficulty, topical hints, code-mixed detection, and a compressed query summary for downstream retrieval.
4. Retrieve candidates: title/body BM25-style scoring, fuzzy similarity, phonetic overlap, semantic similarity, and rescue behavior that expands recall without sacrificing ranking quality.
5. Rerank results: weighted hybrid scoring with phrase overrides, language preference boosts, popularity and recency hooks, and confidence estimation.
6. Enrich the response: explanations, grouped variants, facets, alternate queries, and guided recovery suggestions.

This is implemented primarily in [app/search/query_processor.py](app/search/query_processor.py), [app/search/backend.py](app/search/backend.py), and [app/services/search_service.py](app/services/search_service.py).

## Algorithms And Optimisation Ideas

- BM25-style lexical scoring is computed separately over title terms and broader course text so exact thematic evidence remains prominent across the ranking stack.
- Token-level and whole-query fuzzy repair use explicit confidence thresholds, which keeps autocorrection precise and controlled.
- Compact-query segmentation and no-space recovery allow collapsed inputs to be reconstructed into meaningful search terms.
- Indic transliteration expansion allows romanized queries to recover Hindi catalog items without forcing the user to match the script of the indexed content.
- Phonetic rescue uses Soundex-style overlap to recover plausible matches when spelling quality is poor but pronunciation remains informative.
- Semantic similarity acts as a retrieval and rescue signal, while a local weighted-token fallback preserves functionality when the transformer model is unavailable.
- Weighted reranking combines lexical, fuzzy, phrase, semantic, phonetic, popularity, recency, and language-preference signals into a single score rather than privileging any one technique absolutely.
- Confidence estimation and rescue thresholds control when imperfect but defensible matches should surface, which is an optimisation problem in itself rather than a simple ranking afterthought.
- Deduplication by course group prevents multilingual variants from flooding the top of the result set and preserves result diversity.
- Faceting, alternate queries, grouped suggestions, and recovery guidance extend the optimisation work beyond raw ranking into retrieval usability.

Taken together, these choices make QueryCore a study in practical search optimisation: retrieving the right material robustly under noisy, multilingual, partially transliterated, and domain-specific user input.

## Benchmark Snapshot

From [`artifacts/benchmark_report.json`](artifacts/benchmark_report.json):

- `top1`: `250 / 252` -> `99.2%`
- `top3`: `252 / 252` -> `100%`
- precision guardrail set: `20 / 20` -> `100%`

The evaluation set includes exact-title, acronym, typo, no-space, romanized Hindi, Hindi-script, code-mixed, voice-style, and other generated NLP variants. Those results reflect a retrieval system that is tuned for real user behavior rather than idealized query text.

Current local test run:

- `27 passed, 1 skipped`

The benchmark covers the cases that usually separate average search from excellent search: acronyms, spacing noise, transliterated inputs, query reformulation, voice-style prompts, and precision guardrails under ambiguous traffic.

## Demo UI

The repo includes an interactive search console at `/demo`. It showcases retrieval behavior, result shaping, guided reformulation, and UI-level inspection of the ranking flow.

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
- OpenSearch backend path: adapter validation through Docker.
- Semantic path: sentence-transformers when available, with local fallback behavior.
- Voice path: mock STT by default, `faster-whisper` integration seam available.
- Operational controls: auth middleware, rate limiting, structured error envelopes, analytics logging.

The implementation demonstrates strong retrieval depth, clear architectural layering, and production-conscious backend design.

## Maturity Statement

This repository demonstrates strong command of search optimisation, ranking design, multilingual query handling, transliteration-aware retrieval, fallback strategies, and evaluation-oriented backend engineering. It presents a complete search system with clear algorithmic intent and measurable performance characteristics.

## Project Layout

- `app/api/` REST routes and request wiring
- `app/search/` normalization, repair, retrieval, encoding
- `app/ranking/` hybrid scoring and confidence
- `app/suggest/` grouped autocomplete suggestions
- `app/voice/` speech-to-text adapter seam
- `app/services/` orchestration and response assembly
- `tests/` search, indexing, normalization, failure-mode, suggestion, and integration tests
- `docs/` architecture, deployment, API, evaluation, and Java integration notes

## OpenSearch Validation

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_opensearch.ps1
python .\scripts\opensearch_smoke_test.py
powershell -ExecutionPolicy Bypass -File .\scripts\stop_opensearch.ps1
```

The OpenSearch path allows the same search concepts to be exercised against an external engine-backed deployment flow.

## Additional Documentation

- [docs/architecture.md](docs/architecture.md)
- [docs/search_pipeline.md](docs/search_pipeline.md)
- [docs/testing_and_evaluation.md](docs/testing_and_evaluation.md)
- [docs/java_integration.md](docs/java_integration.md)
- [docs/current_status.md](docs/current_status.md)
