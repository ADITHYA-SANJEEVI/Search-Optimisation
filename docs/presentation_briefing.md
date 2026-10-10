# Current integration note

Real Sphere catalogue sync and IDs-only search are now verified locally. Use [final evidence](FINAL_ADVANCED_SEARCH_INTEGRATION_EVIDENCE.md) for the current integration state; the presentation script below remains for the sample demo. The real OpenSearch adapter persists documents and loads the full local scoring snapshot; it does not currently narrow candidates externally.

# Aastrika Presentation Briefing

## A. 30-Second Pitch

Aastrika is an intelligent course search and matching service for a healthcare learning catalog. It helps users find the most probable course even when their query is incomplete, misspelled, acronym-heavy, multilingual, romanized, or phrased as a natural-language description. The key differentiator is Aastrika PRISM Rank, an explainable ranking algorithm that combines lexical, fuzzy, semantic, phonetic, structured attribute, contextual, quality, popularity, and recency signals.

## B. 2-Minute Technical Explanation

The project is a FastAPI backend with a browser demo and versioned REST API. The UI calls `/api/v1/search`, `/api/v1/suggest`, and optional voice search. API routes validate requests and delegate to service classes. The search service normalizes the query, repairs likely errors, extracts intent, retrieves candidates from an in-memory backend or OpenSearch adapter, reranks candidates with Aastrika PRISM Rank, deduplicates multilingual variants, and returns scores, confidence, explanations, facets, suggestions, and no-result guidance.

The main technologies are Python, FastAPI, Pydantic, RapidFuzz-compatible fuzzy matching, optional sentence-transformers, SQLite analytics, and optional OpenSearch. The local demo path is deterministic and does not require Docker or internet access.

## C. Flagship Algorithm

Name: Aastrika PRISM Rank.

One sentence: Aastrika PRISM Rank scores each course by combining textual precision, semantic relevance, structured intent matches, catalog quality, and conflict penalties.

Intuition: A strong result should not just share a keyword. It should match the topic, wording, language, difficulty, intent, and available course metadata. PRISM lets the system say why a result is first.

Formula: see `docs/aastrika_prism_rank.md` for the exact weighted equation. The main components are BM25-style lexical score, title BM25, fuzzy score, semantic score, phrase match, phonetic overlap, language boost, attribute score, contextual score, quality score, popularity, recency, minus conflict penalties.

Why better than keyword search: it tolerates misspellings, aliases, missing spaces, acronyms, romanized terms, and partial descriptions while still using exact evidence when it exists.

Complexity: in-memory scoring is `O(N * (Q + D))` plus `O(N log N)` sorting. For larger catalogs, OpenSearch should narrow candidates first and PRISM should rerank the top set.

Limitations: weights are hand-tuned, not learned from real traffic; evaluation is on the checked-in sample corpus; terminal display of Hindi text may require UTF-8 output configuration on Windows.

Future improvements: human relevance labels, click feedback, learned weighting, larger OpenSearch-backed retrieval, and continuous relevance dashboards.

## D. 5-7 Minute Live Demo Script

1. Say: "This is a course matching engine for noisy real-world search, not just a search box."
   Run: `powershell -ExecutionPolicy Bypass -File .\launch.ps1`
   Point out: `/demo` opens with the Aastrika course match engine.

2. Say: "First, a clean domain query."
   Search: `postpartum hemorrhage management`
   Point out: PPH results, confidence score, and reasons.

3. Say: "Now the same intent with bad input."
   Search: `PPHHH primary management`
   Point out: correction/recovery and the ranked PPH result.

4. Say: "The algorithm uses more than keyword overlap."
   Search: `beginner pregnancy nutrition in Hindi`
   Point out: safe pregnancy/nutrition result, structured attribute reasons, language/difficulty fit.

5. Say: "It handles romanized language and aliases."
   Search: `sammanjanak matritva dekhbhal`
   Point out: respectful maternity care match.

6. Say: "It behaves gracefully when there is no good answer."
   Search: `quantum astrophysics for toddlers`
   Point out: no-result guidance instead of a crash or fake match.

7. Say: "This is API-backed."
   Open: `/docs` and `/api/v1/ready`
   Point out: stable REST contract, health checks, analytics isolation, indexing endpoints, and demo-ready local launcher.

## E. Employer Questions

1. Why this architecture? It separates API, service orchestration, query processing, backend retrieval, ranking, suggestions, voice, analytics, and schemas, so each part can evolve independently.
2. Why FastAPI? It gives typed request/response validation, interactive docs, and quick backend development.
3. Why not just use an LLM? Search needs deterministic ranking, low latency, explainability, and no hallucinated results. An LLM could later assist query understanding, but PRISM keeps retrieval grounded in catalog data.
4. How does matching work? The query is normalized, repaired, expanded, converted into intent, used to retrieve candidates, and reranked with PRISM.
5. What is the algorithm? Aastrika PRISM Rank, a weighted explainable scoring model across lexical, fuzzy, semantic, phonetic, attribute, context, quality, popularity, recency, and penalties.
6. How do you evaluate accuracy? Existing tests cover search flow, indexing, suggestions, normalization, failure modes, and PRISM behavior. The benchmark artifact reports sample-corpus retrieval performance.
7. How does it scale? The current in-memory backend is for local demos and tests. The OpenSearch adapter persists the catalogue and reloads the full local ranking snapshot; candidate narrowing is a future scaling option.
8. What happens with bad data? Missing fields are scored as lower metadata quality instead of crashing. Conflicting fields create penalties. No strong match returns guidance.
9. What happens with typos? Token repair, fuzzy title/alias matching, compact spacing repair, and phonetic overlap recover likely matches.
10. How does multilingual matching work? Language detection, explicit language preferences, aliases, transliteration expansion, and romanized metadata help bridge query and catalog wording.
11. What did you personally implement? In this pass: PRISM Rank signals/scoring, backend indexing/cache optimizations, PRISM tests, demo score/reason display, and algorithm/presentation docs.
12. Why are weights hand-tuned? There is no real traffic or human-labeled relevance set in the repo, so explainable hand weights are safer than pretending to train a model.
13. What would you build next? Environment onboarding, relevance labels, production OpenSearch sizing, CI/CD, monitoring, and deployment hardening.
14. What is the biggest current weakness? The benchmark is sample-corpus only, not proof of production accuracy on every future catalog or real user query.
15. Is it production ready? It is production-conscious and demo-ready, with typed APIs, health checks, error handling, tests, fallbacks, and docs. Real production still needs environment onboarding, managed infrastructure, secrets, monitoring, and load tests.

## Do Not Demo Today

- Do not claim the system has been trained on real user behavior.
- Do not claim production deployment is complete.
- Do not depend on terminal output to judge Hindi text rendering; use the browser/API response where UTF-8 is handled correctly.
- Do not depend on OpenSearch unless Docker is already running and validated.
