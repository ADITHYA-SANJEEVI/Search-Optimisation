# Architecture

## Overview

The service is a Python 3.11+ FastAPI microservice that exposes a versioned REST API for intelligent course search. It is designed as a standalone search backend that a Java service can call over HTTP without sharing a database or runtime.

## Core layers

- `app/api/`: transport layer and versioned REST routes
- `app/services/`: orchestration for search and indexing flows
- `app/search/`: query preprocessing, repair, encoding, and retrieval backend
- `app/ranking/`: hybrid reranking and confidence scoring
- `app/suggest/`: low-latency dropdown suggestions
- `app/voice/`: STT adapter seam for voice search
- `app/analytics/`: logging and metric hooks
- `app/schemas/`: stable request and response contracts

## Search pipeline

1. Query normalization
2. Repair candidate generation
3. Intent extraction
4. Hybrid retrieval
5. Reranking and confidence scoring
6. Suggestion generation
7. Analytics logging

## Storage model

The implementation uses an in-memory search backend for local execution and tests. That backend is exposed through a `SearchBackend` abstraction so an Elasticsearch/OpenSearch adapter can later replace it without changing REST contracts or orchestration code.

## Integration posture

- JSON-only request/response payloads
- Stable `/api/v1` namespace
- Structured health/readiness/liveness routes
- Idempotent indexing behavior through upsert-style operations
- Explicit error envelopes for Java-side fallback handling
