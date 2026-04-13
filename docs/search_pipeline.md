# Search Pipeline

## 1. Preprocessing

- Unicode normalization
- Lowercasing
- Punctuation and noise stripping
- Repeated-letter normalization
- Whitespace collapse
- Abbreviation expansion
- Filler-word cleanup for voice-style queries

## 2. Query Repair

- Token-level fuzzy repair against indexed vocabulary
- Whole-query fuzzy repair against titles and aliases
- Missing-space and extra-space recovery using compact title matching
- Transliteration normalization through a lightweight Indic map
- Synonym and alias expansion

## 3. Query Understanding

- Language preference extraction
- Code-mixed query detection
- Difficulty extraction
- Topic and educational-goal hints
- Long-query compression into a search summary

## 4. Retrieval

- BM25-style lexical retrieval over title and combined content fields
- Fuzzy rescue using RapidFuzz-compatible scoring
- Phonetic rescue using Soundex-style token comparison
- Semantic similarity via sentence-transformers when available
- Local semantic fallback using weighted token and character n-gram vectors

## 5. Reranking

- Weighted hybrid score
- Exact-title override behavior through phrase boosts
- Language preference boosting
- Popularity and recency hooks
- Confidence estimation for result cards

## 6. Response Enrichment

- Highlighted fields
- Match explanations
- Corrected-query flows
- Facets
- Grouped multilingual variants
- Related suggestions
