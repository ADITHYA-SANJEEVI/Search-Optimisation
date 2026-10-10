# Integration closure map

| Area | Initial inspection | Current state |
| --- | --- | --- |
| Existing search semantics / PRISM | IMPLEMENTED, uncommitted enhancements present | IMPLEMENTED and historical evaluation preserved |
| Catalogue conversion and hard filters | IMPLEMENTED locally | Preserved and exercised by real sync |
| IDs-only `/v1/search` | MISSING | IMPLEMENTED, API and real-index verified |
| limit / offset | PARTIAL (legacy page/page_size) | IMPLEMENTED, before/after-page total verified |
| Browse date order | PARTIAL (recency_score) | IMPLEMENTED actual dates, deterministic IDs as ties |
| Public catalogue sync | MISSING | Full and fingerprint incremental IMPLEMENTED; 620 observed/indexed |
| OpenSearch persistence | PARTIAL; silent memory fallback, fixed cache cap, optimistic writes | Explicit mapping, complete scan, persisted-first writes, readiness verified |
| `publicSearch.ts` in this checkout | MISSING | Exact upstream patch + tested Node helper; upstream merge EXTERNAL INTEGRATION REMAINING |
| Kong boundary | MISSING | CONFIG READY; environment onboarding EXTERNAL ENVIRONMENT BLOCKED |
| Integration documentation | STALE (Java/pagination/sort assumptions) | Current contract/runbook/handoff/evidence updated |
| Previously skipped test | Infrastructure opt-in, Docker stopped | Real local OpenSearch available; full acceptance uses RUN_OPENSEARCH_INTEGRATION=1 |

Only external actions remain: review/merge the Node patch in the actual upstream proxy repository, apply Kong environment configuration and its established authentication policy, deploy/schedule the service and sync, and validate environment-level traffic. No production credentials or deployment access were available or used.

See [final evidence](FINAL_ADVANCED_SEARCH_INTEGRATION_EVIDENCE.md) for exact results and limitations. The real public endpoint is accessible; there is no network blocker for catalogue validation.
