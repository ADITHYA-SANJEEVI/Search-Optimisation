"""Query preprocessing, repair, and intent extraction."""

from __future__ import annotations

from collections import Counter
from functools import lru_cache

from app.core.config import settings
from app.models.query import QueryIntent, QueryState, RepairedQuery
from app.search.backend import InMemorySearchBackend
from app.utils.fuzzy import best_matches, similarity
from app.utils.language import detect_languages, is_code_mixed
from app.utils.text import (
    FILLER_WORDS,
    STOPWORDS,
    apply_transliteration_map,
    compact_text,
    detect_requested_language,
    expand_synonyms,
    extract_difficulty,
    normalize_text,
    normalize_for_match,
    remove_fillers,
    tokenize,
)
from app.utils.transliteration import expand_query_with_transliterations


TOPIC_HINTS = {
    "breastfeeding": ["breastfeeding", "lactation", "nursing"],
    "newborn care": ["newborn", "baby", "infant", "care"],
    "postpartum mental health": ["postpartum", "depression", "mood"],
    "pregnancy nutrition": ["pregnancy", "nutrition", "diet"],
    "infant safety": ["infant", "cpr", "safety"],
}

SEGMENTATION_HINTS = {
    "i",
    "a",
    "course",
    "courses",
    "need",
    "learn",
    "hindi",
    "english",
    "tamil",
    "on",
    "for",
    "family",
    "planning",
    "lam",
    "um",
    "ka",
    "ki",
    "assessment",
    "please",
    "stage",
    "4",
    "monitoring",
    "mother",
    "newborn",
    "condition",
    "evaluation",
    "enbc",
    "high",
    "risk",
    "pregnancy",
    "danger",
    "signs",
    "sign",
    "pph",
    "hrp",
}


class QueryProcessor:
    def __init__(self, backend: InMemorySearchBackend) -> None:
        self.backend = backend

    def _segment_compact_query(self, normalized_query: str) -> str | None:
        if " " in normalized_query or len(normalized_query) < 12 or not normalized_query.isascii():
            return None
        compact_query = compact_text(normalized_query)
        lexicon = {
            compact_text(token): normalize_text(token)
            for token in {
                *self.backend.repair_vocabulary(),
                *SEGMENTATION_HINTS,
                *STOPWORDS,
                *FILLER_WORDS,
            }
            if token
        }
        by_first_char: dict[str, list[tuple[str, str]]] = {}
        for compact_token, token in sorted(lexicon.items(), key=lambda item: len(item[0]), reverse=True):
            if not compact_token:
                continue
            by_first_char.setdefault(compact_token[0], []).append((compact_token, token))

        @lru_cache(maxsize=None)
        def solve(index: int) -> tuple[str, ...] | None:
            if index == len(compact_query):
                return ()
            for compact_token, token in by_first_char.get(compact_query[index], []):
                if compact_query.startswith(compact_token, index):
                    tail = solve(index + len(compact_token))
                    if tail is not None:
                        return (token, *tail)
            return None

        segmented = solve(0)
        if segmented is None or len(segmented) < 2:
            return None
        return " ".join(segmented)

    def _extract_topics(self, tokens: list[str]) -> list[str]:
        topics = []
        token_set = set(tokens)
        for topic, hints in TOPIC_HINTS.items():
            if token_set & set(hints):
                topics.append(topic)
        return topics

    def _educational_goal(self, query: str) -> str | None:
        normalized = normalize_for_match(query)
        if "learn" in normalized or "need" in normalized or "course" in normalized:
            return "guided_learning"
        if "basics" in normalized or "beginner" in normalized:
            return "foundational_learning"
        return None

    def _rewrite_query(self, query: str, topics: list[str], detected_languages: list[str], difficulty: str | None) -> str:
        base_tokens = tokenize(remove_fillers(query), keep_stopwords=False)
        compact = " ".join(base_tokens[:10])
        parts = [compact]
        if topics:
            parts.append(topics[0])
        if difficulty:
            parts.append(difficulty)
        if detected_languages:
            parts.extend(detected_languages[:1])
        return " ".join(dict.fromkeys(" ".join(parts).split()))

    def _repair_spacing(self, normalized_query: str) -> list[RepairedQuery]:
        choices = self.backend.title_choices()
        compact_query = compact_text(normalized_query)
        repairs = []
        for choice, score in best_matches(compact_query, [choice.replace(" ", "") for choice in choices], limit=3):
            if score >= 0.86:
                original = next((item for item in choices if item.replace(" ", "") == choice), None)
                if original and original != normalized_query:
                    repairs.append(RepairedQuery(text=original, confidence=score, source="spacing_repair"))
        return repairs

    def _repair_tokens(self, normalized_query: str) -> list[RepairedQuery]:
        vocabulary = self.backend.repair_vocabulary()
        tokens = tokenize(normalized_query, keep_stopwords=True)
        repaired_tokens = []
        confidence = 1.0
        changed = False
        for token in tokens:
            if token in vocabulary or len(token) <= 2:
                repaired_tokens.append(token)
                continue
            candidates = best_matches(token, vocabulary, limit=1)
            if candidates and candidates[0][1] >= 0.83:
                repaired_tokens.append(candidates[0][0])
                confidence = min(confidence, candidates[0][1])
                changed = True
            else:
                repaired_tokens.append(token)
        if changed:
            return [RepairedQuery(text=" ".join(repaired_tokens), confidence=confidence, source="token_repair")]
        return []

    def _repair_whole_query(self, normalized_query: str) -> list[RepairedQuery]:
        choices = self.backend.title_choices()
        repairs = []
        for choice, score in best_matches(normalized_query, choices, limit=3):
            if score >= 0.82 and choice != normalized_query:
                repairs.append(RepairedQuery(text=choice, confidence=score, source="title_fuzzy_repair"))
        compact_query = compact_text(normalized_query)
        compact_choices = {compact_text(choice): choice for choice in choices}
        for compact_choice, score in best_matches(compact_query, list(compact_choices), limit=3):
            original = compact_choices[compact_choice]
            threshold = 0.74 if " " not in normalized_query and len(compact_query) >= 10 else 0.86
            if score >= threshold and original != normalized_query:
                repairs.append(RepairedQuery(text=original, confidence=score, source="compact_title_repair"))
        return repairs

    def build(self, query: str, requested_filters: dict[str, object], preferred_language: str | None, debug: bool) -> QueryState:
        normalized_query = normalize_for_match(apply_transliteration_map(remove_fillers(query)))
        segmented_query = self._segment_compact_query(normalized_query)
        repair_input = segmented_query or normalized_query
        compact_query = compact_text(repair_input)
        exact_choices = self.backend.title_choices()
        already_normalized_match = repair_input in exact_choices or compact_query in {
            choice.replace(" ", "") for choice in exact_choices
        }
        detected_languages = detect_languages(query)
        explicit_languages = detect_requested_language(query)
        if preferred_language:
            detected_languages.append(normalize_for_match(preferred_language))
        repaired_candidates = []
        repaired_candidates.extend(self._repair_spacing(repair_input))
        repaired_candidates.extend(self._repair_tokens(repair_input))
        repaired_candidates.extend(self._repair_whole_query(repair_input))
        deduped_repairs = []
        seen = set()
        for repair in sorted(repaired_candidates, key=lambda item: item.confidence, reverse=True):
            if repair.text not in seen:
                deduped_repairs.append(repair)
                seen.add(repair.text)
        corrected_query = (
            deduped_repairs[0].text
            if deduped_repairs
            and deduped_repairs[0].confidence >= settings.autocorrect_confidence_threshold
            and not already_normalized_match
            else None
        )
        retrieval_query = (
            corrected_query
            or (deduped_repairs[0].text if deduped_repairs and already_normalized_match else None)
            or segmented_query
            or normalized_query
        )
        did_you_mean = (
            corrected_query
            if corrected_query and similarity(normalized_query, corrected_query) < settings.did_you_mean_similarity_ceiling
            else None
        )
        search_instead_for = query if corrected_query and deduped_repairs[0].confidence >= settings.show_results_for_confidence_threshold else None
        tokens = tokenize(retrieval_query, keep_stopwords=False)
        expanded_terms = list(dict.fromkeys([*expand_synonyms(tokens), *tokenize(" ".join(expand_query_with_transliterations(query)), keep_stopwords=False)]))
        topics = self._extract_topics(expanded_terms)
        difficulty = extract_difficulty(query)
        language_preferences = list(dict.fromkeys([*explicit_languages, *detected_languages]))
        if requested_filters.get("language"):
            language_preferences.append(str(requested_filters["language"]))
        requested_difficulty = str(requested_filters.get("difficulty") or "").strip() or None
        intent = QueryIntent(
            topics=topics,
            specialties=topics,
            language_preferences=language_preferences,
            difficulty=difficulty or requested_difficulty,
            intent_type="course_discovery",
            educational_goal=self._educational_goal(query),
            summary=self._rewrite_query(query, topics, language_preferences, difficulty),
        )
        debug_info = {}
        if debug:
            debug_info = {
                "repair_candidates": [
                    {"text": repair.text, "confidence": repair.confidence, "source": repair.source}
                    for repair in deduped_repairs
                ],
                "retrieval_query": retrieval_query,
                "token_histogram": {key: value for key, value in Counter(tokens).items()},
                "normalized_tokens": tokens,
            }
        return QueryState(
            original_query=query,
            normalized_query=normalized_query,
            compact_query=compact_query,
            normalized_tokens=tokens,
            expanded_terms=expanded_terms,
            detected_languages=sorted(set(language_preferences)),
            is_code_mixed=is_code_mixed(query),
            repaired_candidates=deduped_repairs,
            corrected_query=corrected_query,
            did_you_mean=did_you_mean,
            search_instead_for=search_instead_for,
            intent=intent,
            applied_filters={key: value for key, value in requested_filters.items() if value not in (None, "", [])},
            debug=debug_info,
        )
