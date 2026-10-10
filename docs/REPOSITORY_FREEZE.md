# Sphere advanced search repository freeze - 11 October 2026

Repository-side integration is complete. Local OpenSearch is verified. The exact
Node proxy patch is ready for upstream review and merge; Kong configuration is
ready for environment onboarding. Neither is deployed by this repository freeze.
Production deployment remains external, and no Java backend change is required.

## Preserved project state

The starting implementation branch was
`feature/sphere-contract-adapter-local-20260930-1652`, at
`b2ba79fb4b8a9b1185442753100ae8e75948e6a3`, with substantial completed changes.
All 69 changed/new meaningful files were committed together as
`Preserve completed Sphere advanced search workspace` on
`backup/advanced-search-pre-release` at
`d69207e79a8349ac62f81598e0278bf447fe4d74`. That backup was pushed before cleanup.

`release/advanced-search-final` starts from that preserved commit. Its final
commit message is `Finalize Sphere advanced search integration`; its annotated
tag is `advanced-search-integration-final`. Resolve its SHA without a
self-referencing commit identifier:

```powershell
git rev-parse "advanced-search-integration-final^{commit}"
```

The origin URL formerly used `/ADITHYA-SANJEEVI/aastrika.git`. GitHub confirms
that repository moved to
[ADITHYA-SANJEEVI/Search-Optimisation](https://github.com/ADITHYA-SANJEEVI/Search-Optimisation).
The historical starting SHA exists there, and the authenticated account has push
access. Origin now uses the canonical URL.

## Contract and implementation

`POST /v1/search` returns ranked original IDs and matching total, with optional
query correction. Query results retain PRISM relevance order; browse retains
`lastUpdatedOn` descending order and deterministic ID ties. Limit and offset
apply after filtering and ordering. The Node companion hydrates records
separately and reorders them to the ranked IDs. Full sync, fingerprint incremental
sync, explicit OpenSearch mappings, validation, pagination, quality data,
integration patches, launch scripts, and presentation work are preserved.

Release edits to executable source/tests remove only three extra blank lines at
EOF. Ranking code, expected quality answers, and the exact proxy patch are
unchanged from the backup. `.gitattributes` allows the required single-space
prefix on empty context lines in unified patch files.

## Current acceptance

The single configured Python run passed **90 tests, 0 failures, 0 errors,
0 skips, and 0 xfails** in 522.85 seconds. Results and dependency versions are
recorded in `artifacts/release_checks.json` and `artifacts/release_pytest.xml`.
The commands and environment are in [testing_and_evaluation.md](testing_and_evaluation.md).
Python uses the sample backend for ordinary tests and real isolated OpenSearch
indexes for opt-in infrastructure tests. Semantic model downloads are disabled; the existing cached
`sentence-transformers/all-MiniLM-L6-v2` model was loaded. The single Node run
passed all 7 tests with no failures/skips/TODOs. The single offline benchmark
retained 250/252 top-1, 252/252 top-3, and 20/20 negatives; all measured per-tag
results match the preserved report. Expected answers were not edited.

Local Docker OpenSearch 2.19.1 restarted using its existing named volume. The
catalogue index was green with 620 persisted documents; the single-node cluster
was yellow. That count describes the retained local snapshot, not today's public
source total. No fresh full/incremental source sync or production mutation was
performed. Existing 7 October live validation and sync evidence remains intact.

## Hygiene and audit

Publishable files were checked for provider tokens, private keys, JWTs, literal
Bearer credentials, credential-bearing URLs, and credential assignments.
The five assignment matches were manually reviewed: the `.env.example`
placeholder, the development-only launcher key, and three ordinary code
expressions. No real secrets or captured authentication material were found.
The largest retained file is a deliberate demo screenshot of 261,649 bytes;
there are no files above 5 MiB.

Git and Docker build exclusions cover local environment files (while retaining
`.env.example`), virtual environments, model caches, bytecode, test caches,
runtime captures, logs, PID files, local fixtures, private key/credential files,
and local OpenSearch state. No excluded file was force-added. Runtime material
is retained locally and excluded from publication. Automatic policy review
blocked removal of the temporary ignored proxy patch-check directory, without
a more specific reason; its patch application check passed.

Intentional benchmark, sync, live-validation, and JUnit reports remain checked
in. Historical `final_checks.json`, `final_pytest.xml`, and
`final_health_pytest.xml` retain their original dates and results. Useful technical
progress and presentation documents were preserved.

## Publication verification

Push the backup, release branch, and annotated tag without force or changes to
main. Verify the remote release SHA equals local HEAD and the peeled tag commit:

```powershell
git status --short
git rev-parse HEAD
git rev-parse "advanced-search-integration-final^{commit}"
git ls-remote --heads origin backup/advanced-search-pre-release release/advanced-search-final
git ls-remote --tags origin advanced-search-integration-final "advanced-search-integration-final^{}"
```

## External remaining work

Review, merge, and build the exact patch in the upstream proxy repository;
onboard Kong with the environment's authentication policy; deploy the API and
persistent index; schedule catalogue sync and coordinate API snapshot refresh;
run platform traffic acceptance. No upstream merge, Kong deployment, production
deployment, or automatic merge into main is claimed.
