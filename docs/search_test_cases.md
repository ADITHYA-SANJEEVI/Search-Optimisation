# Search Test Cases And Acceptance Metrics

This document defines the demo evaluation bar for the Aastrika Sphere intelligent search service against the current course catalog.

## Scope

The evaluation covers:

- exact title search
- typo recovery
- whitespace recovery
- acronym and abbreviation expansion
- transliteration-aware retrieval
- mixed Hindi/English query handling
- word-order robustness
- punctuation and repeated-character noise
- competency-name retrieval
- level-aware matching
- multilingual ranking preference
- suggestion quality
- voice-search pipeline readiness

## 30 Metrics

1. `Top1 Exact Title Accuracy >= 95%`
2. `Top3 Exact Title Recall >= 99%`
3. `Top1 One-Edit Typo Accuracy >= 90%`
4. `Top3 One-Edit Typo Recall >= 95%`
5. `Top1 Severe Misspelling Rescue >= 75%`
6. `No-Space Query Recovery >= 90%`
7. `Extra-Space Query Recovery >= 95%`
8. `Punctuation-Noise Robustness >= 95%`
9. `Repeated-Letter Spam Recovery >= 90%`
10. `Word-Order Invariance >= 90%`
11. `Abbreviation Expansion Accuracy >= 95%`
12. `Acronym Expansion Accuracy >= 95%`
13. `Romanized Hindi Query Recall@3 >= 85%`
14. `Hindi Script Query Recall@3 >= 95%`
15. `Code-Mixed Query Recall@3 >= 90%`
16. `Competency Name Retrieval Accuracy >= 90%`
17. `Level-Aware Query Accuracy >= 85%`
18. `Language Preference Boost Accuracy >= 90%`
19. `Did-You-Mean Accuracy >= 85%`
20. `Search-Instead-For Trigger Precision >= 85%`
21. `Suggestion Precision@5 >= 80%`
22. `Related Query Coverage >= 80%`
23. `Facet Correctness >= 99%`
24. `Grouped Variant Correctness >= 99%`
25. `Zero-Result Precision >= 95%`
26. `False-Positive Guardrail For Out-Of-Domain Queries >= 95%`
27. `Voice Transcript Cleanup Pass Rate >= 90%`
28. `Voice End-To-End Search Recall@3 >= 85%`
29. `P95 Local Demo Latency <= 1200ms`
30. `Benchmark Regression Pass Rate = 100%`

## Required Query Families

- Exact course title: `Emergency triage assessment`
- Title fragment: `triage assessment`
- Typo: `lactaion counsler`
- Severe typo: `prasvottar raktasrav mulyakn`
- No spaces: `respectfulmaternitycare`
- Extra spaces: `   normal   delivery   `
- Word reorder: `pregnancy fever` vs `fever in pregnancy`
- Acronym: `KMC`, `PPH`, `ENBC`, `LAM`, `ANC`, `HRP`
- Romanized Hindi: `garbhavastha khatre sanket`, `mutra janch`, `sammanjanak matritva dekhbhal`
- Mixed language: `newborn ke danger signs`, `PPH ka primary management`
- Competency query: `Stage 4 monitoring of mother and newborn`
- Level query: `level 5 postpartum hemorrhage`
- Natural-language intent: `I need a Hindi course on family planning and LAM`
- Voice-style noisy query: `um pph ka assessment please`

## Acceptance Rules

- A query passes if the expected `group_id` is rank 1 for Top1 metrics or appears in top 3 for Recall@3 metrics.
- If a query explicitly requests a language, the first result must either match that language or be a grouped parent with the requested-language variant surfaced.
- Out-of-domain queries must not return high-confidence medical matches.
- Corrections should not fire when an exact normalized title already exists.

## Dataset Sources

- `sample_data/courses.json`
- `sample_data/evaluation_queries.json`

## Reporting

The benchmark script must emit:

- overall Top1 and Top3
- per-tag Top1 and Top3
- language-preference success
- correction success
- zero-result precision
- failures with offending query text and returned group ids
