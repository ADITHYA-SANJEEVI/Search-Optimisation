# API Contract

## Versioning

- Base path: `/api/v1`
- Response contract includes `schema_version`
- Error responses return `schema_version`, `request_id`, and a structured `error` object

## Search

`POST /api/v1/search`

Request fields:

- `query`
- `filters.language`
- `filters.category`
- `filters.topic`
- `filters.instructor`
- `filters.difficulty`
- `filters.duration_max`
- `filters.certification`
- `page`
- `page_size`
- `sort`
- `preferred_language`
- `debug`

Response highlights:

- `original_query`
- `normalized_query`
- `corrected_query`
- `did_you_mean`
- `search_instead_for`
- `detected_languages`
- `extracted_search_intent`
- `results`
- `grouped_suggestions`
- `alternate_queries`
- `no_results_guidance`
- `facets`
- `pagination`
- `debug_info`

## Suggest

`GET /api/v1/suggest?q=...&preferred_language=tamil`

Returns grouped sections such as:

- `corrected_query`
- `course_titles`
- `topics`
- `instructors`
- `related_queries`
- `language_aware`

## Voice Search

`POST /api/v1/search/voice`

- multipart upload with `file`
- validates supported audio content types
- returns transcript metadata and nested `search_response`
- degrades gracefully when STT is unavailable

## Indexing

- `POST /api/v1/index/bulk`
- `POST /api/v1/index/update`
- `POST /api/v1/index/delete`
- `POST /api/v1/index/reindex`

Bulk and update are idempotent upserts keyed by `course_id`.

## Health

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/live`
