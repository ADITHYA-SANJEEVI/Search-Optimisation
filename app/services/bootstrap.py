"""Application bootstrap and dependency wiring."""

from __future__ import annotations

from dataclasses import dataclass

from app.analytics.storage import SQLiteAnalyticsStore
from app.analytics.tracker import AnalyticsTracker
from app.core.config import settings
from app.ranking.reranker import HybridReranker
from app.search.backend import InMemorySearchBackend
from app.search.encoder import SemanticEncoder
from app.search.opensearch_backend import OpenSearchBackedSearchBackend
from app.search.query_processor import QueryProcessor
from app.services.index_service import IndexService
from app.services.search_service import SearchService
from app.suggest.service import SuggestService
from app.voice.transcription import TranscriptionAdapter, build_transcription_adapter


@dataclass(slots=True)
class ServiceContainer:
    encoder: SemanticEncoder
    backend: InMemorySearchBackend
    analytics: AnalyticsTracker
    query_processor: QueryProcessor
    reranker: HybridReranker
    suggester: SuggestService
    search_service: SearchService
    index_service: IndexService
    transcription_adapter: TranscriptionAdapter


def build_container() -> ServiceContainer:
    encoder = SemanticEncoder()
    backend: InMemorySearchBackend
    if settings.search_backend.lower() == "opensearch":
        try:
            backend = OpenSearchBackedSearchBackend(encoder=encoder)
        except Exception:
            backend = InMemorySearchBackend(encoder=encoder)
    else:
        backend = InMemorySearchBackend(encoder=encoder)
    analytics_store = None
    if settings.analytics_enabled:
        try:
            analytics_store = SQLiteAnalyticsStore(settings.analytics_db_path)
        except Exception:
            analytics_store = None
    analytics = AnalyticsTracker(store=analytics_store)
    query_processor = QueryProcessor(backend=backend)
    reranker = HybridReranker()
    suggester = SuggestService(backend=backend, query_processor=query_processor)
    search_service = SearchService(
        backend=backend,
        query_processor=query_processor,
        reranker=reranker,
        suggester=suggester,
        encoder=encoder,
        analytics=analytics,
    )
    index_service = IndexService(backend=backend)
    transcription_adapter = build_transcription_adapter()
    container = ServiceContainer(
        encoder=encoder,
        backend=backend,
        analytics=analytics,
        query_processor=query_processor,
        reranker=reranker,
        suggester=suggester,
        search_service=search_service,
        index_service=index_service,
        transcription_adapter=transcription_adapter,
    )
    if settings.bootstrap_sample_data:
        index_service.load_sample_data()
    return container
