# Testing and Evaluation

## Current automated test status

Run:

```powershell
pytest -q
```

Current local result:

- `26 passed, 1 skipped`

Covered areas:

- normalization and query repair
- search flow and ranking behavior
- suggest endpoint behavior
- indexing endpoints
- failure modes and structured errors
- auth and rate limiting
- request-size and audio-size limits
- analytics persistence and fallback behavior
- voice endpoint behavior
- optional OpenSearch integration smoke validation behind `RUN_OPENSEARCH_INTEGRATION=1`

## Benchmark runner

Run:

```powershell
python .\scripts\run_benchmark.py
```

The benchmark uses the curated evaluation set in `sample_data/evaluation_queries.json` and writes its report to `artifacts/benchmark_report.json`.

Current benchmark summary:

- `top1=250/252 (99%)`
- `top3=252/252 (100%)`
- `negative_no_result_pass=20/20 (100%)`

## Evaluation focus

The current benchmark set covers 150+ style cases across:

- exact title
- exact topic
- typo recovery
- repeated-letter recovery
- no-space recovery
- extra-space recovery
- natural-language phrasing
- code-mixed queries
- Hindi script
- romanized Hindi
- acronym and abbreviation queries
- language preference
- competency and level-oriented queries
- negative queries with expected no-result behavior

## Voice validation note

The API supports:

- deterministic mock transcription for local/demo verification
- a `faster-whisper` integration path for real STT

This repository does not currently claim broad real-world audio validation across accents, languages, or noisy environments.

## Honest interpretation

The current evaluation evidence is strong for a domain-focused backend prototype and demo submission. It is enough to support claims around tested and benchmarked hybrid retrieval, but it should not be overstated as universal or web-scale validation.
