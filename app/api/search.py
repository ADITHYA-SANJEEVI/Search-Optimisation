"""Search and suggestion endpoints."""

from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.deps import get_container
from app.core.config import settings
from app.core.errors import ServiceError
from app.schemas.common import SuggestionGroup
from app.schemas.search import SearchRequest, SearchResponse
from app.schemas.voice import VoiceSearchResponse
from app.services.bootstrap import ServiceContainer
from app.utils.text import remove_fillers

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest, container: ServiceContainer = Depends(get_container)) -> SearchResponse:
    return container.search_service.search(request, route_type="search")


@router.get("/suggest", response_model=list[SuggestionGroup])
def suggest(
    q: str = Query(..., min_length=1),
    preferred_language: str | None = Query(default=None),
    limit: int = Query(default=8, ge=1, le=10),
    container: ServiceContainer = Depends(get_container),
) -> list[SuggestionGroup]:
    started = perf_counter()
    response = container.suggester.suggest(q, preferred_language, limit=limit)
    container.analytics.record_search(
        q,
        sum(len(group.items) for group in response),
        (perf_counter() - started) * 1000,
        normalized_query=q,
        route_type="suggest",
        metadata={"preferred_language": preferred_language, "sections": [group.section for group in response]},
    )
    return response


@router.post("/search/voice", response_model=VoiceSearchResponse)
async def voice_search(
    file: UploadFile = File(...),
    preferred_language: str | None = Query(default=None),
    debug: bool = Query(default=False),
    container: ServiceContainer = Depends(get_container),
) -> VoiceSearchResponse:
    content_type = (file.content_type or "").strip().lower()
    normalized_content_type = content_type.split(";", 1)[0].strip()
    if normalized_content_type not in settings.allowed_audio_types:
        raise ServiceError(
            "unsupported_audio_type",
            "Unsupported audio format",
            status_code=415,
            details={
                "allowed_types": list(settings.allowed_audio_types),
                "received_type": content_type,
                "normalized_type": normalized_content_type,
            },
        )
    payload = await file.read()
    if len(payload) > settings.max_audio_upload_bytes:
        raise ServiceError(
            "audio_too_large",
            "Audio payload exceeds configured size limit",
            status_code=413,
            details={"max_audio_upload_bytes": settings.max_audio_upload_bytes, "received_bytes": len(payload)},
        )
    try:
        transcription = container.transcription_adapter.transcribe(
            file.filename or "voice-query.wav",
            normalized_content_type,
            payload,
        )
        cleaned = remove_fillers(transcription.transcript)
        search_response = container.search_service.search(
            SearchRequest(query=cleaned, preferred_language=preferred_language, debug=debug),
            route_type="voice_search",
        )
        return VoiceSearchResponse(
            schema_version=settings.schema_version,
            transcript=transcription.transcript,
            transcript_cleaned=cleaned,
            transcription_confidence=transcription.confidence,
            degraded=False,
            search_response=search_response,
            metadata={"filename": file.filename},
        )
    except ServiceError as exc:
        container.analytics.record_search(
            file.filename or "voice-query.wav",
            0,
            0.0,
            normalized_query=None,
            corrected_query=None,
            route_type="voice_search",
            degraded=True,
            metadata={"reason": exc.message, "filename": file.filename, "content_type": normalized_content_type},
        )
        return VoiceSearchResponse(
            schema_version=settings.schema_version,
            degraded=True,
            degradation_reason=exc.message,
            metadata={"code": exc.code, "filename": file.filename},
        )
