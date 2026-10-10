# Current status ? 7 October 2026

COMPLETE WITH EXTERNAL DEPLOYMENT BLOCKERS.

The repository-owned Sphere integration is implemented and locally validated: IDs-only `/v1/search`, relevance-ranked query results, date-ordered browse, bounded limit/offset, supported filters, real public catalogue sync, persisted OpenSearch documents, safe startup/readiness behavior, tested Node proxy helper, exact upstream patch, and Kong configuration handoff. No Java or LERN change is required.

Real data: full sync observed and indexed 620 Live Courses across seven pages, zero rejected. Incremental mode observed 620 unchanged records, zero upserts, index count still 620. Two optional competency fields produced type warnings and were ignored by the existing adapter; all required fields were accepted.

Validation: 90 Python tests passed with RUN_OPENSEARCH_INTEGRATION=1, zero failures/errors/skips/xfails; 7 Node contract tests passed; 2 targeted readiness/index tests passed after the final health refinement. Existing benchmark: 250/252 positive top-1, 252/252 top-3, 20/20 negatives, unchanged measured results. These are sample-corpus metrics, not production relevance judgments.

The actual upstream proxy repository was not modified. `integration/ui-proxy/publicSearch.patch` applies to the inspected upstream snapshot and its exact companion passed local contract and real-record hydration tests. Kong configuration is ready but not onboarded. Production deployment, scheduling, upstream build/merge, and environment-level acceptance remain external actions.

No final commit was created: the starting dirty tree includes earlier ranking/catalogue changes mixed with demo branding, browser voice, presentation documentation, and launcher edits. This pass relies on some of those changes in shared files; staging everything would include unrelated work. All preexisting work is preserved; HEAD is unchanged and nothing was pushed.

See [FINAL_ADVANCED_SEARCH_INTEGRATION_EVIDENCE.md](FINAL_ADVANCED_SEARCH_INTEGRATION_EVIDENCE.md) for exact commands, counts, limitations, and changed files. Use [deployment.md](deployment.md) for real catalogue operations; `launch.ps1` is the sample presentation flow.
