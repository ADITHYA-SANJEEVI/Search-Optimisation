# Sphere Advanced Search API contract

## Service and gateway

Internal: `POST /v1/search`. Expected Kong route: `POST /apis/proxies/v8/advanced-search/v1/search`. The gateway manifest is configuration ready; no external deployment is claimed.

```json
{"query":"postpartm hemorhage managment","filters":{},"limit":1,"offset":0}
```

```json
{"ids":["do_1143024882114969601461"],"total":99,"corrected_query":"postpartum hemorrhage management"}
```

This query/first-ID/total/correction pair was exercised on the real catalogue; the multi-ID smoke response is in `artifacts/sphere_live_acceptance.json`. `ids` and `total` are mandatory. `corrected_query` is emitted only when the current repair engine supplies it. Full records, internal scores, and debug fields are excluded. Suggestions are not added to this boundary.

`query` is optional, defaults to an empty string, and accepts at most 240 characters. Null and non-string values are rejected. Whitespace-only input browses. `limit` is a strict integer 1..100 (default 10); `offset` is a strict integer 0..1,000,000 (default 0). Unknown fields and invalid filter shapes return 422. A required index outage returns a safe 503 error envelope.

## Order and population

Query search retains the existing normalization, typo/compact-query repair, synonyms/acronyms, transliteration, intent, retrieval guardrails, and PRISM relevance score. Descending score then exact course ID determines order. There is no caller sort parameter, so dates cannot replace query relevance. Browse orders actual parsed `lastUpdatedOn` descending, missing dates last, then exact course ID ascending. The service always restricts eligibility to active Live Courses.

Filters precede pagination. Total counts the matching unique course-ID population before offset/limit; no group-level collapse is applied to this IDs boundary. The existing demo API continues its original grouped result semantics. Offset at or beyond total returns an empty IDs page with the same total.

## Supported filters

Sphere aliases: `primaryCategory` (array), `contentType` (array), `status` (array), mapping to internal `categories`, `content_types`, `publication_statuses`. Internal spellings are also accepted individually. Scalar supported filters: `language`, `category`, `topic`, `instructor`, `difficulty`, `duration_max`, `certification`. Matching retains existing case-normalized exact filter semantics. Missing optional course metadata is not manufactured; e.g. upstream duration is retained as presentation metadata without inferring minutes.

The adapter preserves canonical identifiers byte-for-byte. Source name, subtitle/instructions, language, keywords, category, content type, status, supported competency JSON, and dates populate the existing document model. Serialized competency arrays are decoded; incompatible optional types are diagnosed and ignored. Image URLs/ratings/durations stay presentation metadata and do not become search evidence.

`translate_sphere_request` supports limit/offset in the nested or outer request, rejects conflicting pagination/query values, and accepts `lastUpdatedOn desc` only as a source instruction: it selects date ordering for browse and relevance for a query. Unsupported sorting/filters are rejected. This helper does not change any existing public API.

The existing `/api/v1/search` API remains a sample/demo response with full records. The UI proxy fetches actual full records separately from `publicContent/v1/search` by exact identifier.
