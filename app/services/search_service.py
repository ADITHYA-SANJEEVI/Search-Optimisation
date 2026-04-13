"""Search orchestration service."""

from __future__ import annotations

import math
from time import perf_counter

from app.analytics.tracker import AnalyticsTracker
from app.core.config import settings
from app.core.errors import ServiceError
from app.models.course import SearchCandidate
from app.ranking.reranker import HybridReranker
from app.schemas.common import HighlightFields, Pagination
from app.schemas.search import (
    CourseVariant,
    NoResultsGuidance,
    SearchIntentPayload,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.search.backend import InMemorySearchBackend
from app.search.encoder import SemanticEncoder
from app.search.query_processor import QueryProcessor
from app.suggest.service import SuggestService
from app.utils.text import compact_text, filter_retrieval_terms, normalize_for_match, soundex, tokenize


class SearchService:
    def __init__(
        self,
        backend: InMemorySearchBackend,
        query_processor: QueryProcessor,
        reranker: HybridReranker,
        suggester: SuggestService,
        encoder: SemanticEncoder,
        analytics: AnalyticsTracker,
    ) -> None:
        self.backend = backend
        self.query_processor = query_processor
        self.reranker = reranker
        self.suggester = suggester
        self.encoder = encoder
        self.analytics = analytics

    def _passes_filters(self, candidate: SearchCandidate, filters: dict[str, object]) -> bool:
        course = candidate.course
        if filters.get("language") and course.language != normalize_for_match(str(filters["language"])):
            return False
        if filters.get("category") and normalize_for_match(course.category) != normalize_for_match(str(filters["category"])):
            return False
        if filters.get("topic") and normalize_for_match(course.topic) != normalize_for_match(str(filters["topic"])):
            return False
        if filters.get("instructor") and course.instructor_normalized != normalize_for_match(str(filters["instructor"])):
            return False
        if filters.get("difficulty") and normalize_for_match(course.difficulty or "") != normalize_for_match(str(filters["difficulty"])):
            return False
        if filters.get("duration_max") and course.duration_minutes and course.duration_minutes > int(filters["duration_max"]):
            return False
        if filters.get("certification") is not None and course.certification != bool(filters["certification"]):
            return False
        return course.active

    def _sort_candidates(self, candidates: list[SearchCandidate], sort: str) -> list[SearchCandidate]:
        if sort == "popularity":
            return sorted(
                candidates,
                key=lambda item: (item.course.popularity_score, item.score_breakdown.get("total", 0.0)),
                reverse=True,
            )
        if sort == "newest":
            return sorted(
                candidates,
                key=lambda item: (item.course.recency_score, item.score_breakdown.get("total", 0.0)),
                reverse=True,
            )
        if sort == "alphabetical":
            return sorted(candidates, key=lambda item: item.course.title.lower())
        if sort == "recommended":
            return sorted(
                candidates,
                key=lambda item: (
                    item.score_breakdown.get("total", 0.0),
                    item.course.popularity_score,
                    item.course.recency_score,
                ),
                reverse=True,
            )
        return sorted(candidates, key=lambda item: item.score_breakdown.get("total", 0.0), reverse=True)

    def _facet_counts(self, candidates: list[SearchCandidate]) -> dict[str, dict[str, int]]:
        facets = {"language": {}, "topic": {}, "difficulty": {}}
        for candidate in candidates:
            facets["language"][candidate.course.language] = facets["language"].get(candidate.course.language, 0) + 1
            facets["topic"][candidate.course.topic] = facets["topic"].get(candidate.course.topic, 0) + 1
            if candidate.course.difficulty:
                facets["difficulty"][candidate.course.difficulty] = (
                    facets["difficulty"].get(candidate.course.difficulty, 0) + 1
                )
        return facets

    def _highlight(self, text: str, tokens: list[str]) -> str:
        highlighted = text
        for token in sorted(set(tokens), key=len, reverse=True):
            if len(token) < 3:
                continue
            highlighted = highlighted.replace(token, f"<em>{token}</em>")
            highlighted = highlighted.replace(token.title(), f"<em>{token.title()}</em>")
        return highlighted

    def _result_item(self, candidate: SearchCandidate, query_terms: list[str], debug: bool) -> SearchResultItem:
        course = candidate.course
        grouped_variants = [
            CourseVariant(course_id=variant.course_id, title=variant.title, language=variant.language)
            for variant in self.backend.grouped_variants(course.group_id, course.course_id)
        ]
        confidence = self.reranker.confidence(candidate)
        return SearchResultItem(
            course_id=course.course_id,
            group_id=course.group_id,
            title=course.title,
            description=course.description,
            instructor=course.instructor,
            language=course.language,
            available_languages=course.available_languages,
            category=course.category,
            topic=course.topic,
            difficulty=course.difficulty,
            duration_minutes=course.duration_minutes,
            certification=course.certification,
            metadata={
                **course.metadata,
                "competency_name": course.competency_name,
                "levels": course.levels,
                "updated_on": course.updated_on,
            },
            score=round(candidate.score_breakdown.get("total", 0.0), 4),
            confidence=round(confidence, 4),
            matched_terms=sorted(set(candidate.matched_terms)),
            explanations=candidate.explanations,
            highlights=HighlightFields(
                title=self._highlight(course.title, query_terms),
                description=self._highlight(course.description, query_terms),
                tags=[self._highlight(tag, query_terms) for tag in course.tags],
            ),
            grouped_variants=grouped_variants,
            debug=candidate.score_breakdown if debug else {},
        )

    def _no_results_guidance(self, state_query: str, filters: dict[str, object], alternate_queries: list[str]) -> NoResultsGuidance:
        suggestions = [
            "Try fewer words or remove a filter",
            "Try the corrected query suggestion if shown",
            "Search by topic, for example 'lactation' or 'newborn care'",
        ]
        suggestions.extend(alternate_queries[:2])
        relax = [key for key, value in filters.items() if value not in (None, "", [])]
        return NoResultsGuidance(
            message=f"No strong results found for '{state_query}'.",
            suggestions=list(dict.fromkeys(suggestions)),
            filters_to_relax=relax,
        )

    def _retrieve_candidates(self, state) -> list[SearchCandidate]:
        query_terms = filter_retrieval_terms(list(dict.fromkeys([*state.normalized_tokens, *state.expanded_terms])))
        semantic_query = state.corrected_query or state.intent.summary or state.normalized_query
        semantic_vector = self.encoder.encode(semantic_query)
        phonetic_terms = [soundex(token) for token in query_terms]
        candidates = []
        for document in self.backend.all_documents():
            candidate = self.backend.build_candidate(
                document,
                normalized_query=state.corrected_query or state.normalized_query,
                compact_query=compact_text(state.corrected_query or state.normalized_query),
                query_terms=query_terms,
                semantic_vector=semantic_vector,
                preferred_languages=state.intent.language_preferences,
                phonetic_terms=phonetic_terms,
            )
            self.reranker.score(candidate)
            if self._passes_filters(candidate, state.applied_filters):
                total = candidate.score_breakdown.get("total", 0.0)
                matched_term_count = len(set(candidate.matched_terms))
                domain_evidence = (
                    matched_term_count >= 2
                    or candidate.title_bm25_score > 0
                    or candidate.phrase_score > 0.0
                    or candidate.fuzzy_score >= 0.72
                    or candidate.semantic_score >= settings.semantic_rescue_threshold + 0.04
                    or candidate.phonetic_score >= 0.5
                )
                rescue = (
                    candidate.fuzzy_score >= settings.fuzzy_rescue_threshold
                    or (
                        candidate.semantic_score >= settings.semantic_rescue_threshold
                        and (
                            candidate.matched_terms
                            or candidate.fuzzy_score >= 0.55
                            or candidate.phonetic_score >= 0.34
                            or candidate.title_bm25_score > 0
                        )
                    )
                    or candidate.phrase_score > 0.0
                )
                strong_enough = total > settings.min_candidate_score and domain_evidence
                if strong_enough or rescue:
                    candidates.append(candidate)
        if not candidates and state.corrected_query and state.corrected_query != state.normalized_query:
            fallback_terms = tokenize(state.corrected_query, keep_stopwords=False)
            semantic_vector = self.encoder.encode(state.corrected_query)
            for document in self.backend.all_documents():
                candidate = self.backend.build_candidate(
                    document,
                    normalized_query=state.corrected_query,
                    compact_query=compact_text(state.corrected_query),
                    query_terms=fallback_terms,
                    semantic_vector=semantic_vector,
                    preferred_languages=state.intent.language_preferences,
                    phonetic_terms=[soundex(token) for token in fallback_terms],
                )
                self.reranker.score(candidate)
                if self._passes_filters(candidate, state.applied_filters):
                    if candidate.score_breakdown.get("total", 0.0) > 0.0:
                        candidates.append(candidate)
        return candidates

    def search(self, request: SearchRequest, *, route_type: str = "search") -> SearchResponse:
        if not request.query or not request.query.strip():
            raise ServiceError("empty_query", "Search query must not be empty", status_code=400)
        if len(request.query) > settings.max_query_length:
            raise ServiceError(
                "query_too_long",
                "Search query exceeded the maximum supported length",
                status_code=400,
                details={"max_query_length": settings.max_query_length},
            )
        started = perf_counter()
        filters = request.filters.model_dump() if hasattr(request.filters, "model_dump") else request.filters.dict()
        state = self.query_processor.build(
            query=request.query,
            requested_filters=filters,
            preferred_language=request.preferred_language,
            debug=request.debug,
        )
        candidates = self._retrieve_candidates(state)
        sorted_candidates = self._sort_candidates(candidates, request.sort)
        facets = self._facet_counts(sorted_candidates)
        deduped = []
        seen_groups = set()
        for candidate in sorted_candidates:
            identity = candidate.course.group_id
            if identity in seen_groups:
                continue
            seen_groups.add(identity)
            deduped.append(candidate)
        page_size = max(1, min(request.page_size, settings.max_page_size))
        page = max(1, int(request.cursor)) if request.cursor and request.cursor.isdigit() else max(1, request.page)
        total = len(deduped)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = deduped[start:end]
        response_results = [self._result_item(candidate, state.expanded_terms, request.debug) for candidate in page_items]
        latency_ms = (perf_counter() - started) * 1000
        self.analytics.record_search(
            state.original_query,
            len(response_results),
            latency_ms,
            normalized_query=state.normalized_query,
            corrected_query=state.corrected_query,
            route_type=route_type,
            metadata={
                "filters_applied": state.applied_filters,
                "detected_languages": state.detected_languages,
                "sort": request.sort,
            },
        )
        if state.corrected_query:
            self.analytics.record_correction(state.original_query, state.corrected_query, route_type=route_type)
        grouped_suggestions = self.suggester.suggest(request.query, request.preferred_language, limit=5)
        alternate_queries = [repair.text for repair in state.repaired_candidates[1:4]]
        no_results = None
        if not response_results:
            no_results = self._no_results_guidance(
                state.corrected_query or state.normalized_query,
                state.applied_filters,
                alternate_queries,
            )
        pagination = Pagination(
            page=page,
            page_size=page_size,
            total_results=total,
            total_pages=max(math.ceil(total / page_size), 1) if total else 0,
            next_cursor=str(page + 1) if end < total else None,
        )
        debug_info = None
        if request.debug and settings.enable_debug_payloads:
            debug_info = {
                "query_pipeline": state.debug,
                "semantic_model_available": self.encoder._model is not None,
                "latency_ms": round(latency_ms, 2),
            }
        return SearchResponse(
            schema_version=settings.schema_version,
            original_query=state.original_query,
            normalized_query=state.normalized_query,
            corrected_query=state.corrected_query,
            did_you_mean=state.did_you_mean,
            search_instead_for=state.search_instead_for,
            detected_languages=state.detected_languages,
            extracted_search_intent=SearchIntentPayload(
                intent_type=state.intent.intent_type,
                topics=state.intent.topics,
                specialties=state.intent.specialties,
                language_preferences=state.intent.language_preferences,
                difficulty=state.intent.difficulty,
                educational_goal=state.intent.educational_goal,
                summary=state.intent.summary,
            ),
            filters_applied=state.applied_filters,
            results=response_results,
            grouped_suggestions=grouped_suggestions,
            alternate_queries=alternate_queries,
            no_results_guidance=no_results,
            facets=facets,
            pagination=pagination,
            debug_info=debug_info,
        )
