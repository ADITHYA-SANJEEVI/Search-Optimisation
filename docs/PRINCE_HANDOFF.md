# Handoff to Prince

The Python service implements the 1 October contract at `POST /v1/search`: original IDs plus total, optional corrected query, strict limit/offset, relevance for queries and actual date order for browse. Existing PRISM semantics are retained. Real public sync observed 620 Live Courses across seven pages on 7 October 2026, indexed all 620, and an incremental rerun performed zero upserts.

## Actual proxy boundary

No `publicSearch.ts` exists in this checkout. The read-only public upstream source was inspected at [Sphere/sunbird-cb-uiproxy](https://github.com/Sphere/sunbird-cb-uiproxy/blob/d85cc8ca5f898919a61bae5dd0823d08ad305d50/src/publicApi_v8/publicSearch.ts), branch `cbrelease-4.0.1`, commit `d85cc8ca5f898919a61bae5dd0823d08ad305d50`. The exact unified patch is `integration/ui-proxy/publicSearch.patch`; it adds the locally tested companion `advancedSearch.ts` to `src/publicApi_v8/` and inserts one feature-flag branch in `/getCourses`. Patch application was checked against that source snapshot. No upstream repository was modified or merged.

```powershell
git apply --check path/to/publicSearch.patch
git apply path/to/publicSearch.patch
```

Perform these commands in the upstream repository after reviewing changes against its actual target revision. Run its normal TypeScript/build tests there; this checkout verifies the TypeScript helper by Node type stripping and contract/live tests, not a full upstream application build.

## Required Node environment

- `ADVANCED_SEARCH_ENABLED=false` by default; only literal `true` enables it.
- `ADVANCED_SEARCH_URL=http://<internal-service>:8000/v1/search`, or the approved external Kong URL ending `/apis/proxies/v8/advanced-search/v1/search`.
- `ADVANCED_SEARCH_TIMEOUT_MS=3000`, bounded to 1..30000; invalid settings retain legacy behavior.

Supported query requests forward query, supported filters, limit (default 10), and offset (default 0). Unknown UI filters, invalid pagination, flag-off requests, and browse requests take the original path. Advanced dependency/malformed response/record-fetch failure also returns directly to the original handler, avoiding recursion. The legacy browse behavior and public/LERN APIs remain unchanged.

The companion receives only IDs/total, fetches public records by exact identifier with offset 0 and limit equal to the ranked page size, and never sends query sorting to that hydration request. Records are mapped by identifier and emitted in ranked-ID order; unexpected extra records are discarded, duplicate fetched IDs retain their first record, and absent IDs are omitted. The upstream handler's existing `!competency` visibility rule is preserved. Consequently hydrated content may be shorter than the ranked page while `count` retains the Advanced matching-population total. The live test demonstrated this: three ranked IDs, two visible fetched records, one excluded competency record. Facets come from the existing public fetch and are page-level; no new global facet aggregation is claimed.

## Kong handoff

`integration/kong/advanced-search.yml` is CONFIG READY ONLY. It maps POST `/apis/proxies/v8/advanced-search/v1/search` to the internal `/v1/search`, strips the external path, and configures bounded timeouts and zero retries. Replace host/port through the environment owner's normal onboarding process and apply existing gateway auth policy. No Kong credentials were present; no route was deployed or tested through Kong.

## Remaining external actions

Review and merge the patch in the actual proxy repository; run upstream build and platform acceptance; onboard the Kong service/route; deploy the API and persistent index; schedule sync and coordinate API snapshot refresh/restart. There is no Java change. No remote push was performed.

See [final evidence](FINAL_ADVANCED_SEARCH_INTEGRATION_EVIDENCE.md) for exact commands, test results, security checks, and repository state.
