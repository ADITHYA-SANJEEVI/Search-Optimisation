# Architecture

Python FastAPI owns `/v1/search`, validation, and service orchestration. The existing QueryProcessor and PRISM ranker retain richer search semantics. OpenSearch owns persistent course documents with canonical keyword IDs and explicit sortable dates. Startup scans the entire index into the existing scoring snapshot; query requests score that complete population before paging. No new search engine or Java layer is introduced.

The catalogue sync calls the read-only Sphere public API with Live Course filters, limit, and offset, validates records through the existing adapter, then upserts by original identifier. Incremental mode still scans the complete public population and compares content fingerprints stored in index metadata. It is not an upstream delta feed. Completed rejection-free traversals remove absent source-owned records. Rejected records suppress pruning, preserving prior indexed records until repaired.

The existing Node UI proxy feature flag calls Advanced Search only for applicable queries, receives IDs, fetches full public records, and reorders them by those IDs. A failure returns control to the original legacy handler without recursion. Browse stays on the existing proxy path; `/v1/search` also supports date-ordered browse for direct consumers.

External CLI sync and a running API have separate snapshots. Stop/restart the API after syncing externally; production scheduling and coordinated refresh ownership remain deployment tasks. Readiness checks index existence, cluster availability, cached/indexed count reconciliation, and a populated catalogue. Empty indexes return warming/503. Liveness reports process availability without backend I/O. An explicitly configured OpenSearch startup failure is fatal rather than silently switching to memory.

The `/api/v1` routes and browser demo remain a separate existing evaluation surface. Search analytics are noncritical; cached semantic models and the existing local fallback are supported. No models are added by this integration.
