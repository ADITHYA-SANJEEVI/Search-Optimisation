"""Low-latency suggestion generation."""

from __future__ import annotations

from collections import defaultdict

from app.schemas.common import SuggestionGroup, SuggestionItem
from app.search.backend import InMemorySearchBackend
from app.search.query_processor import QueryProcessor
from app.utils.fuzzy import best_matches
from app.utils.text import normalize_for_match


class SuggestService:
    def __init__(self, backend: InMemorySearchBackend, query_processor: QueryProcessor) -> None:
        self.backend = backend
        self.query_processor = query_processor

    def suggest(self, query: str, preferred_language: str | None, limit: int = 8) -> list[SuggestionGroup]:
        normalized = normalize_for_match(query)
        state = self.query_processor.build(
            query=query,
            requested_filters={},
            preferred_language=preferred_language,
            debug=False,
        )
        buckets: dict[str, list[SuggestionItem]] = defaultdict(list)

        if state.did_you_mean:
            buckets["corrected_query"].append(
                SuggestionItem(text=state.did_you_mean, type="did_you_mean", confidence=0.93, metadata={})
            )

        title_choices = []
        topic_choices = set()
        instructor_choices = set()
        for document in self.backend.all_documents():
            title_choices.append(document.title)
            topic_choices.add(document.topic)
            instructor_choices.add(document.instructor)
            if normalized and normalized in document.title_normalized:
                buckets["course_titles"].append(
                    SuggestionItem(
                        text=document.title,
                        type="course_title",
                        confidence=0.88,
                        metadata={"language": document.language, "course_id": document.course_id},
                    )
                )

        for text, score in best_matches(query, title_choices, limit=limit):
            buckets["course_titles"].append(
                SuggestionItem(text=text, type="course_title", confidence=score, metadata={})
            )
        for text, score in best_matches(query, sorted(topic_choices), limit=max(3, limit // 2)):
            buckets["topics"].append(SuggestionItem(text=text, type="topic", confidence=score, metadata={}))
        for text, score in best_matches(query, sorted(instructor_choices), limit=max(3, limit // 3)):
            buckets["instructors"].append(
                SuggestionItem(text=text, type="instructor", confidence=score, metadata={})
            )

        related_queries = []
        for document in self.backend.all_documents():
            for candidate in document.suggestion_terms:
                if normalized and normalized in normalize_for_match(candidate):
                    related_queries.append(candidate)
        for candidate in list(dict.fromkeys(related_queries))[:limit]:
            buckets["related_queries"].append(
                SuggestionItem(text=candidate, type="related_query", confidence=0.74, metadata={})
            )

        if preferred_language:
            buckets["language_aware"].append(
                SuggestionItem(
                    text=f"{query} in {preferred_language}",
                    type="language_aware",
                    confidence=0.71,
                    metadata={"preferred_language": preferred_language},
                )
            )

        groups = []
        for section, items in buckets.items():
            deduped = []
            seen = set()
            for item in sorted(items, key=lambda value: value.confidence, reverse=True):
                if item.text.lower() not in seen:
                    deduped.append(item)
                    seen.add(item.text.lower())
                if len(deduped) >= limit:
                    break
            if deduped:
                groups.append(SuggestionGroup(section=section, items=deduped))
        return groups
