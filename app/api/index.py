"""Indexing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.core.config import settings
from app.schemas.indexing import (
    BulkIndexRequest,
    DeleteIndexRequest,
    IndexingResponse,
    ReindexRequest,
    UpdateIndexRequest,
)
from app.services.bootstrap import ServiceContainer

router = APIRouter(prefix="/index", tags=["index"])


@router.post("/bulk", response_model=IndexingResponse)
def bulk_index(request: BulkIndexRequest, container: ServiceContainer = Depends(get_container)) -> IndexingResponse:
    indexed = container.index_service.bulk_index(request.documents)
    return IndexingResponse(
        schema_version=settings.schema_version,
        indexed_count=indexed,
        total_documents=container.backend.document_count(),
        detail="Bulk index completed",
    )


@router.post("/update", response_model=IndexingResponse)
def update_index(request: UpdateIndexRequest, container: ServiceContainer = Depends(get_container)) -> IndexingResponse:
    container.index_service.update(request.document)
    return IndexingResponse(
        schema_version=settings.schema_version,
        indexed_count=1,
        total_documents=container.backend.document_count(),
        detail="Document upserted",
    )


@router.post("/delete", response_model=IndexingResponse)
def delete_index(request: DeleteIndexRequest, container: ServiceContainer = Depends(get_container)) -> IndexingResponse:
    deleted = container.index_service.delete(request.course_ids)
    return IndexingResponse(
        schema_version=settings.schema_version,
        deleted_count=deleted,
        total_documents=container.backend.document_count(),
        detail="Documents deleted",
    )


@router.post("/reindex", response_model=IndexingResponse)
def reindex(request: ReindexRequest, container: ServiceContainer = Depends(get_container)) -> IndexingResponse:
    indexed = container.index_service.reindex(request.documents, request.reload_sample_data)
    return IndexingResponse(
        schema_version=settings.schema_version,
        indexed_count=indexed,
        total_documents=container.backend.document_count(),
        detail="Reindex completed",
    )
