"""Frozen Sphere IDs-only boundary; the demo contract remains separate."""
from fastapi import APIRouter, Depends

from app.api.deps import get_container
from app.schemas.search import AdvancedSearchRequest, AdvancedSearchResponse
from app.services.bootstrap import ServiceContainer

router = APIRouter()


@router.post("/v1/search", response_model=AdvancedSearchResponse, response_model_exclude_none=True)
def advanced_search(request: AdvancedSearchRequest, container: ServiceContainer = Depends(get_container)):
    return container.search_service.search_ids(request)
