# Aastrika PRISM Rank

Aastrika PRISM Rank is the project flagship ranking algorithm for matching natural-language course descriptions to the most probable Aastrika catalog item.

PRISM stands for Precision, Relevance, Intent, Signal quality, and Metadata. The score combines text retrieval evidence with structured catalog evidence so the system can explain why a course ranked highly.

## Scoring Model

For a candidate course `c` and processed query `q`, the implementation computes:

```text
PRISM(c, q) =
  0.32 * lexical_bm25
+ 0.18 * title_bm25
+ 0.14 * fuzzy_similarity
+ 0.18 * semantic_similarity
+ 0.08 * phrase_match
+ 0.04 * phonetic_overlap
+ 0.06 * language_boost
+ 0.12 * attribute_match
+ 0.08 * contextual_fit
+ 0.04 * metadata_quality
+ 0.03 * popularity
+ 0.01 * recency
- 0.18 * conflict_penalty
```

Weights are configurable through environment variables in `app/core/config.py`.

## Signals

- `lexical_bm25`: BM25-style score over title, aliases, synonyms, descriptions, tags, instructor, topic, category, and metadata.
- `title_bm25`: title-only BM25-style score so exact course naming remains important.
- `fuzzy_similarity`: typo-tolerant title and alias similarity.
- `semantic_similarity`: sentence-transformer similarity when a local model is present, otherwise a deterministic weighted token and character-ngram fallback.
- `phrase_match`: exact or normalized title, alias, no-space title, or description phrase evidence.
- `phonetic_overlap`: Soundex-style overlap for spelling and pronunciation-like errors.
- `language_boost`: boost when the result language matches detected or requested language preferences.
- `attribute_match`: structured agreement with topic, category, competency, difficulty, and language.
- `contextual_fit`: learning-goal, topic, and code-mixed/multilingual fit.
- `metadata_quality`: completeness of fields needed for confident presentation and filtering.
- `conflict_penalty`: penalty for requested difficulty, language, or topic conflicts.

## Why It Beats Keyword Matching

Keyword matching only asks whether words overlap. PRISM asks a broader question: does this course look like the best answer to the user's intent? It can recover from typos, missing spaces, synonyms, romanized terms, and partial descriptions while still favoring exact and structured evidence.

## Complexity

For the in-memory backend, each query scores every indexed document.

- Query preprocessing: approximately `O(T * V)` for fuzzy repair over query tokens and repair vocabulary, improved by cached vocabularies.
- Candidate scoring: `O(N * (Q + D))`, where `N` is documents, `Q` is query terms, and `D` is the average candidate token/phonetic evidence touched.
- Sorting: `O(N log N)`.
- Space: `O(N * D)` for indexed token counters and semantic fallback vectors.

For larger catalogs, the same scoring model should be used after a search engine retrieves a smaller candidate set.

## Implementation

- Scorer: `app/ranking/reranker.py`
- Candidate signal construction: `app/search/backend.py` and `app/services/search_service.py`
- API exposure: result `score`, `confidence`, `explanations`, and debug `score_breakdown`
- Tests: `tests/test_prism_rank.py`

## Limitations

The current implementation is deterministic and explainable, but it is still hand-weighted. It has not been trained against real user judgments. Hindi-script content is stored as UTF-8 and works in the app/API, but some Windows terminals may display it incorrectly unless their output encoding is configured for UTF-8.

Future improvements should add click/conversion feedback, human relevance judgments, offline nDCG/MRR evaluation, OpenSearch candidate retrieval at larger scale, and learned weight tuning.
