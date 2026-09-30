# Sphere API adapter — implementation brief (feature branch)

## Objective
Integrate the existing QueryCore search engine with the real Sphere catalogue and its observed `getCourses` request structure **without replacing the production Sphere API, modifying production, or changing search/ranking internals**.

Current repository components:
- `app/api/search.py`: `POST /api/v1/search`
- `app/schemas/search.py`: `SearchRequest`, `SearchFilters`, `SearchResponse`
- `app/schemas/indexing.py`: `CourseDocumentPayload`
- `app/services/index_service.py`: bulk/upsert facilities
- `app/core/security.py`: auth/rate-limit middleware
- `docs/java_integration.md`: Java client integration contract

## Verified upstream request
`POST https://sphere.aastrika.org/apis/public/v8/publicSearch/getCourses`

```json
{
  "request": {
    "query": "pregnancy",
    "filters": {
      "primaryCategory": ["Course"],
      "contentType": ["Course"],
      "status": ["Live"]
    }
  },
  "query": "pregnancy",
  "sort": [{"lastUpdatedOn": "desc"}]
}
```

Observed request context: locale, org, rootOrg, hostPath, wid. Do **not** accept forwarded browser cookies, copy another user's session, or mistake contextual headers for authorization. Actual trusted Java context mapping needs confirmation.

## Verified upstream response facts
- `responseCode: "OK"`, `status: 200`
- `result.content`: array of original Sphere course records
- `result.count`: reported count
- An empty result also included `result.facets: []`; populated response example did not include facets. Treat facets as optional.
- Normal-query reported results: `pregnancy` 28, `nutrition` 13, `course` 89; typo `pregranct` yielded zero. These are observations, not quality/coverage guarantees.
- Sample populated records have `identifier` (canonical ID), `name`, `subTitle`, `instructions`, `keywords`, `language` (array), `primaryCategory`, `contentType`, `status`, `competencies_v1` (string containing JSON), `lastUpdatedOn`, `averageRating`, `thumbnail`, `appIcon`, and `duration` (units unverified).
- A sample can simultaneously have `status: Live` and `isRejected: true`; do not infer new business policy from isRejected.

## Local input fixtures
Developer has already captured `sphere-pregnancy.json`, `sphere-nutrition.json`, `sphere-course.json`, `sphere-response.json` in their home directory. These are **not** present in GitHub. Copy to `.local-fixtures/` locally and exclude that directory from commits. Do not upload raw production/catalogue captures or any cookies to this public repository. Derive small synthetic or reviewed public-field-only fixtures for CI.

## Tasks

### 1. Baseline audit
Run `python -m pytest -q` in a configured environment. Record results. Inspect relevant modules and current schema, ensuring existing tests remain unchanged. Do not claim an old README test count is current.

### 2. Catalogue ingestion adapter
Create a narrow adapter module (e.g. `app/integrations/sphere_catalog.py`) that maps upstream `result.content[]` records to `CourseDocumentPayload`. Handle absent and incorrectly typed optional fields defensively; produce explicit diagnostics for unmappable records and do not silently lose records.

Tentative mapping to verify against *all available local fixtures*:
- `identifier` -> `course_id` (exactly; no generated IDs)
- `name` -> `title`
- `subTitle` and `instructions` -> nonempty, deduplicated `description`
- `keywords` -> `tags`
- `language` array -> `available_languages`; choose a documented scalar `language`
- `primaryCategory` -> `category`
- parse `competencies_v1` JSON string into `competency_name`/`levels`/`topic` if verified; avoid treating raw JSON as searchable prose
- `lastUpdatedOn` -> `updated_on`
- preserve `thumbnail`, `appIcon`, unknown display metadata without giving those fields unsafe ranking influence
- `group_id`: use canonical ID as a safe initial fallback unless verified grouping metadata exists
- `duration`: retain raw if units are unconfirmed; do not assume seconds vs minutes
- `averageRating`: preserve raw; do not map directly to a normalized popularity score without explicit policy
- derive activity only from verified business semantics, not from contradictory fields.

Ensure no production changes, no hardcoded credentials, no background catalogue scraping.

### 3. Request adapter
Implement a pure, unit-testable translator for the observed upstream request -> internal `SearchRequest`. Explicitly handle the two query fields: reject conflicting nonblank values; report missing/empty values consistently. Parse known filters and sorting. Do not silently drop `status`, `contentType`, and `primaryCategory` if they are required hard filters: either enforce before/after ranking using trusted metadata or reject/mark the request as unsupported with an explicit integration gap. `lastUpdatedOn desc` and `relevance` have different semantics: document and test sort choice rather than silently substituting.

### 4. API boundary
Keep `POST /api/v1/search` compatible. Choose a minimal internal compatibility surface only if justified; don't shadow public `/apis/public/v8/publicSearch/getCourses` or claim to replace it. Java owns authentication, original course records and UI. Preferred Python response remains ordered canonical IDs with relevance metadata; only emulate original full course envelopes if Prince verifies that is essential.

### 5. Verification
Add dedicated unit tests and integration tests using synthetic sanitized fixtures:
- course ID, name, language-array mapping, serialized competency parsing
- missing optional fields and malformed essential records
- nested vs top-level query conflicts
- known/unknown filters and sorting semantics
- empty response, optional facets, count semantics
- preserving search ranking and canonical IDs after local indexing
- existing endpoint backward compatibility
- no confidential headers or cookies in output/logs.
Check source `result.count` may differ from returned content length when pagination is present; don't assert equality universally. Don't assert production data correctness from one screenshot.

### 6. Deliverables
- Adapter modules, tests and documentation
- `docs/SPHERE_API_CONTRACT.md`: observed contract and field mapping
- `docs/INTEGRATION_GAPS.md`: exact missing Java DTO/response expectations, trusted context, pagination, sort/filter semantics, catalog synchronization
- `docs/PRINCE_HANDOFF.md`: what works, run instructions, actual test output, minimal Java integration sample, remaining questions.
- An example local-only import command that creates a reversible dev index and doesn't overwrite other sample data unexpectedly.

Implement on `feature/sphere-contract-adapter`. Don't push, merge or expose raw fixtures without owner's review. Do not claim complete Java or production integration without Java-side validation.
