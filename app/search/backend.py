"""Index backend abstraction and in-memory implementation."""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable

from app.models.course import IndexedCourse, SearchCandidate
from app.schemas.indexing import CourseDocumentPayload
from app.search.encoder import SemanticEncoder
from app.utils.fuzzy import partial_similarity, similarity, token_similarity
from app.utils.text import build_weighted_counter, compact_text, normalize_for_match, soundex, tokenize
from app.utils.transliteration import generate_transliterations


class SearchBackend:
    """Elasticsearch/OpenSearch-style indexing abstraction."""

    def bulk_upsert(self, documents: list[CourseDocumentPayload]) -> int:
        raise NotImplementedError

    def upsert_one(self, document: CourseDocumentPayload) -> None:
        raise NotImplementedError

    def delete_many(self, course_ids: list[str]) -> int:
        raise NotImplementedError

    def all_documents(self) -> list[IndexedCourse]:
        raise NotImplementedError

    def vocabulary(self) -> list[str]:
        raise NotImplementedError

    def repair_vocabulary(self) -> list[str]:
        raise NotImplementedError


class InMemorySearchBackend(SearchBackend):
    """Search backend suitable for local execution and tests."""

    def __init__(self, encoder: SemanticEncoder) -> None:
        self.encoder = encoder
        self._documents: dict[str, IndexedCourse] = {}
        self._idf: dict[str, float] = {}
        self._avg_all_len = 1.0
        self._avg_title_len = 1.0

    def _prepare_document(self, payload: CourseDocumentPayload) -> IndexedCourse:
        auto_transliterations = []
        for text in [payload.title, *payload.aliases, payload.competency_name or ""]:
            auto_transliterations.extend(generate_transliterations(text))
        merged_transliterations = list(dict.fromkeys([*payload.transliterations, *auto_transliterations]))
        aliases_normalized = [normalize_for_match(alias) for alias in payload.aliases]
        title_normalized = normalize_for_match(payload.title)
        description_normalized = normalize_for_match(payload.description)
        title_terms = tokenize(payload.title, keep_stopwords=False)
        metadata_text = " ".join(
            [
                payload.competency_name or "",
                " ".join(payload.levels),
                payload.updated_on or "",
                " ".join(str(value) for value in payload.metadata.values()),
            ]
        )
        all_text = " ".join(
            [
                payload.title,
                " ".join(payload.aliases),
                " ".join(payload.synonyms),
                " ".join(merged_transliterations),
                payload.description,
                " ".join(payload.tags),
                payload.instructor,
                payload.topic,
                payload.category,
                payload.language,
                metadata_text,
            ]
        )
        all_terms = tokenize(all_text, keep_stopwords=False)
        semantic_text = " ".join(
            [
                payload.title,
                payload.description,
                " ".join(payload.tags),
                " ".join(payload.aliases),
                " ".join(payload.synonyms),
                " ".join(merged_transliterations),
                payload.topic,
                payload.language,
                metadata_text,
            ]
        )
        suggestion_terms = list(
            dict.fromkeys(
                [
                    payload.title,
                    *payload.aliases,
                    *payload.tags,
                    payload.topic,
                    payload.instructor,
                    payload.language,
                    payload.competency_name or "",
                    *payload.levels,
                ]
            )
        )
        return IndexedCourse(
            course_id=payload.course_id,
            group_id=payload.group_id or payload.course_id,
            title=payload.title,
            title_normalized=title_normalized,
            title_no_spaces=compact_text(payload.title),
            aliases=payload.aliases,
            aliases_normalized=aliases_normalized,
            synonyms=payload.synonyms,
            transliterations=merged_transliterations,
            description=payload.description,
            description_normalized=description_normalized,
            tags=payload.tags,
            instructor=payload.instructor,
            instructor_normalized=normalize_for_match(payload.instructor),
            language=normalize_for_match(payload.language),
            available_languages=[normalize_for_match(language) for language in payload.available_languages],
            category=payload.category,
            topic=payload.topic,
            competency_name=payload.competency_name,
            levels=payload.levels,
            updated_on=payload.updated_on,
            difficulty=payload.difficulty,
            duration_minutes=payload.duration_minutes,
            certification=payload.certification,
            popularity_score=payload.popularity_score,
            recency_score=payload.recency_score,
            active=payload.active,
            metadata=payload.metadata,
            suggestion_terms=suggestion_terms,
            semantic_text=semantic_text,
            semantic_vector=self.encoder.encode(semantic_text),
            title_terms=title_terms,
            all_terms=all_terms,
            title_frequencies=Counter(title_terms),
            all_frequencies=Counter(all_terms),
        )

    def _recompute_stats(self) -> None:
        corpus_size = max(len(self._documents), 1)
        document_frequencies: Counter[str] = Counter()
        title_lengths = []
        body_lengths = []
        for document in self._documents.values():
            title_lengths.append(len(document.title_terms))
            body_lengths.append(len(document.all_terms))
            document_frequencies.update(set(document.all_terms))
        self._idf = {
            token: math.log(1 + (corpus_size - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequencies.items()
        }
        self._avg_title_len = max(sum(title_lengths) / max(len(title_lengths), 1), 1.0)
        self._avg_all_len = max(sum(body_lengths) / max(len(body_lengths), 1), 1.0)

    def bulk_upsert(self, documents: list[CourseDocumentPayload]) -> int:
        for document in documents:
            self.upsert_one(document)
        return len(documents)

    def upsert_one(self, document: CourseDocumentPayload) -> None:
        self._documents[document.course_id] = self._prepare_document(document)
        self._recompute_stats()

    def delete_many(self, course_ids: list[str]) -> int:
        deleted = 0
        for course_id in course_ids:
            if course_id in self._documents:
                del self._documents[course_id]
                deleted += 1
        self._recompute_stats()
        return deleted

    def all_documents(self) -> list[IndexedCourse]:
        return list(self._documents.values())

    def document_count(self) -> int:
        return len(self._documents)

    def vocabulary(self) -> list[str]:
        terms = set()
        for document in self._documents.values():
            terms.update(document.all_terms)
            terms.update(document.title_terms)
            terms.update(tokenize(" ".join(document.aliases), keep_stopwords=False))
            terms.update(tokenize(" ".join(document.transliterations), keep_stopwords=False))
        return sorted(terms)

    def repair_vocabulary(self) -> list[str]:
        terms = set()
        for document in self._documents.values():
            terms.update(document.title_terms)
            terms.update(tokenize(" ".join(document.aliases), keep_stopwords=False))
            terms.update(tokenize(" ".join(document.tags), keep_stopwords=False))
            terms.update(tokenize(" ".join(document.transliterations), keep_stopwords=False))
            if document.competency_name:
                terms.update(tokenize(document.competency_name, keep_stopwords=False))
        return sorted(terms)

    def title_choices(self) -> list[str]:
        values = []
        for document in self._documents.values():
            values.append(document.title_normalized)
            values.extend(document.aliases_normalized)
        return sorted(set(values))

    def grouped_variants(self, group_id: str, exclude_course_id: str) -> list[IndexedCourse]:
        return [
            document
            for document in self._documents.values()
            if document.group_id == group_id and document.course_id != exclude_course_id and document.active
        ]

    def _bm25(self, query_terms: Iterable[str], frequencies: Counter[str], avg_len: float) -> float:
        k1 = 1.5
        b = 0.75
        document_length = max(sum(frequencies.values()), 1)
        score = 0.0
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if frequency == 0:
                continue
            idf = self._idf.get(term, 0.0)
            numerator = frequency * (k1 + 1)
            denominator = frequency + k1 * (1 - b + b * document_length / avg_len)
            score += idf * (numerator / denominator)
        return score

    def build_candidate(
        self,
        document: IndexedCourse,
        *,
        normalized_query: str,
        compact_query: str,
        query_terms: list[str],
        semantic_vector: dict[str, float],
        preferred_languages: list[str],
        phonetic_terms: list[str],
    ) -> SearchCandidate:
        compact_aliases = [compact_text(alias) for alias in document.aliases]
        title_bm25 = self._bm25(query_terms, document.title_frequencies, self._avg_title_len)
        lexical_bm25 = self._bm25(query_terms, document.all_frequencies, self._avg_all_len)
        phrase_score = 1.0 if normalized_query and normalized_query in document.description_normalized else 0.0
        if normalized_query == document.title_normalized or normalized_query in document.aliases_normalized:
            phrase_score = max(phrase_score, 3.0)
        if compact_query and compact_query == document.title_no_spaces:
            phrase_score = max(phrase_score, 2.6)
        if compact_query and compact_query in compact_aliases:
            phrase_score = max(phrase_score, 2.4)
        fuzzy_score = max(
            similarity(normalized_query, document.title_normalized),
            partial_similarity(normalized_query, document.title_normalized),
            max((token_similarity(normalized_query, alias) for alias in document.aliases_normalized), default=0.0),
            similarity(compact_query, document.title_no_spaces),
            partial_similarity(compact_query, document.title_no_spaces),
            max((similarity(compact_query, alias) for alias in compact_aliases), default=0.0),
            max((partial_similarity(compact_query, alias) for alias in compact_aliases), default=0.0),
        )
        semantic_score = self.encoder.similarity(semantic_vector, document.semantic_vector)
        matched_terms = [term for term in query_terms if term in document.all_frequencies]
        phonetic_hits = 0
        document_phonetics = {soundex(term) for term in document.title_terms + document.all_terms if term}
        for code in phonetic_terms:
            if code and code in document_phonetics:
                phonetic_hits += 1
        phonetic_score = phonetic_hits / max(len(phonetic_terms), 1)
        language_boost = 1.0 if preferred_languages and document.language in preferred_languages else 0.0
        explanations = []
        if phrase_score >= 1.2:
            explanations.append("Exact or normalized title match")
        elif phrase_score > 0.0:
            explanations.append("Query phrase found in course content")
        if lexical_bm25 > 0:
            explanations.append("Lexical BM25 match on title, tags, or description")
        if fuzzy_score >= 0.8:
            explanations.append("Typo-tolerant fuzzy match")
        if semantic_score >= 0.4:
            explanations.append("Semantic retrieval rescue")
        if language_boost > 0:
            explanations.append("Preferred language boost applied")
        return SearchCandidate(
            course=document,
            lexical_score=lexical_bm25,
            title_bm25_score=title_bm25,
            fuzzy_score=fuzzy_score,
            phrase_score=phrase_score,
            semantic_score=semantic_score,
            phonetic_score=phonetic_score,
            language_boost=language_boost,
            popularity_score=document.popularity_score,
            recency_score=document.recency_score,
            matched_terms=matched_terms,
            explanations=explanations,
            score_breakdown={},
        )
