# Java Integration

## Calling pattern

The Java backend should treat this service as a downstream search dependency and call it over HTTP using JSON contracts only. No shared database assumptions are required.

## Recommended endpoint usage

- `POST /api/v1/search` for full search result pages
- `GET /api/v1/suggest` for search-bar dropdown suggestions
- `POST /api/v1/search/voice` if the Java backend proxies audio uploads
- `POST /api/v1/index/bulk` for initial course catalog sync
- `POST /api/v1/index/update` for single-course upserts
- `POST /api/v1/index/delete` for deactivate/remove flows
- `POST /api/v1/index/reindex` for full rebuilds
- `GET /api/v1/ready` before routing production traffic

## Indexing flow

1. Publish course changes from the Java system as JSON payloads keyed by `course_id`.
2. Use `index/update` for single-record changes and `index/bulk` for larger batches.
3. Treat indexing as idempotent. Safe retries are possible because repeated upserts overwrite the same logical course document.
4. Store `group_id` consistently for multilingual variants of the same course.

## Timeout and retry guidance

- Keep search request timeouts tight, typically 500-1500 ms at the Java client.
- Retry indexing requests on transient 5xx or timeout failures with the same idempotency key.
- Avoid blind retries for search requests unless the Java backend has a user-safe fallback path.

## Service-unavailable fallback

If this service is unavailable, the Java backend should:

1. Fall back to existing literal search or cached popular courses.
2. Surface a soft-degradation state to the frontend rather than a blank failure.
3. Disable advanced correction banners if the search service was not reached.

## Spring Boot wrapping approach

Use a dedicated client component, for example a `SearchIntelligenceClient`, backed by `WebClient` or `RestClient`.

- Serialize request DTOs to the exact JSON schema
- Map error envelopes into typed exceptions
- Apply circuit breaking and timeout budgets
- Optionally cache `suggest` responses briefly for dropdown latency reduction

## Deployment note

The Java backend should not couple itself to implementation details such as Python models, local indexing strategy, or the in-memory backend. Only the REST contract should be treated as stable.
