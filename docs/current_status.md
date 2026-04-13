# Current Status

This repository currently stands as a Java-compatible intelligent search backend and production-oriented backend prototype for healthcare course discovery. The codebase is intentionally scoped for a stable internship/demo checkpoint rather than a broad rewrite or speculative optimization pass.

## Current position

The project can be positioned as:

- a Java-compatible intelligent search backend
- a production-oriented backend prototype
- a hybrid lexical + fuzzy + semantic retrieval system
- multilingual and transliteration-aware for healthcare course discovery
- integration-ready over REST
- benchmarked and tested

The project should not be positioned as:

- Google-level
- web-scale
- fully enterprise-ready in every dimension
- mandatory-OpenSearch-only
- fully voice-validated across all accents and languages

## Implemented backend scope

The current codebase includes:

- FastAPI backend with versioned `/api/v1` endpoints
- search, suggest, voice search, indexing, delete, reindex, health, readiness, and liveness routes
- Java-friendly JSON contracts with Pydantic schemas
- query normalization and conversational cleanup
- typo tolerance, spacing repair, abbreviation handling, synonym expansion, and transliteration-aware expansion
- language preference, difficulty, topic, and educational-goal hint extraction
- Hindi script, romanized Hindi, and code-mixed query support within project scope
- hybrid lexical + fuzzy + semantic retrieval with reranking
- exact-title and compact-title override behavior
- highlights, explanations, confidence scores, grouped variants, corrected query flow, alternate queries, facets, pagination, and no-results guidance
- grouped suggestion buckets for dropdown UX
- voice-search-ready endpoint with mock and `faster-whisper` paths
- in-memory backend for local/demo mode
- optional OpenSearch adapter and Docker wiring
- API-key auth, rate limiting, request-size limits, and safer production error mode
- persistent analytics storage via SQLite with non-fatal fallback behavior
- query and correction logging hooks

Primary files:

- `app/main.py`
- `app/api/`
- `app/search/`
- `app/services/`
- `app/analytics/`
- `app/core/`

## Demo and verification support

The repository now includes a tiny built-in verification UI at `/demo` for:

- search submission
- grouped suggestions from `/api/v1/suggest`
- corrected query and alternate query inspection
- health and dependency checks
- audio upload and browser-mic testing against `/api/v1/search/voice`

This page is intentionally lightweight and does not introduce a frontend build system.

## Validation evidence

### Automated tests

Current local test result:

- `pytest -q`
- `26 passed, 1 skipped`

Coverage includes:

- normalization
- search flow
- suggestions
- indexing
- failure modes
- auth and rate limiting
- analytics persistence and fallback behavior
- voice endpoint behavior
- optional OpenSearch smoke coverage behind an explicit flag

### Benchmark

Current benchmark artifact:

- [`artifacts/benchmark_report.json`](../artifacts/benchmark_report.json)

Current summary:

- `top1=250/252 (99%)`
- `top3=252/252 (100%)`
- `negative_no_result_pass=20/20 (100%)`

The evaluation set covers 150+ style cases and includes exact-title, typo, no-space, extra-space, natural-language, acronym, code-mixed, Hindi-script, romanized Hindi, and negative-query behavior.

## Runtime model

Default local mode:

- in-memory backend
- sample data bootstrap enabled
- mock voice path enabled
- analytics SQLite enabled
- auth disabled unless explicitly turned on
- rate limiting disabled unless explicitly turned on

Optional validation path:

- OpenSearch via Docker
- `faster-whisper` path when configured

OpenSearch remains optional and is not required for the default backend demo.

## Remaining limitations

The current checkpoint is stable and submission-ready for internship/demo purposes, but these limits remain:

- OpenSearch is implemented and smoke-testable, but not required for normal local use
- voice support is practical and integration-ready, but not broadly validated across real multilingual audio conditions
- multilingual handling is domain-focused rather than a full cross-lingual platform
- operational hardening remains prototype-level rather than full enterprise depth

## Wrap-up status

At this checkpoint, the project is honestly defensible as a Java-compatible intelligent search backend with hybrid lexical + fuzzy + semantic retrieval, multilingual and transliteration-aware healthcare course discovery, indexing APIs, voice-search-ready architecture, analytics, auth, rate limiting, tests, and benchmark evaluation.
