from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from api.db.database import get_async_db
from api.models.models import Note
from api.models.schemas import SearchRequest, SearchResponse, SearchResult
from api.search.vector_search import search_notes, rebuild_index_for_org

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(
    search_request: SearchRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Search for notes using vector similarity
    """
    # Use default org_id
    org_id = "default"

    # Search for notes
    results = await search_notes(
        query=search_request.query, org_id=org_id, top_k=search_request.top_k, db=db
    )

    # Format results
    search_results = [
        SearchResult(note_id=note_id, score=score) for note_id, score in results
    ]

    return SearchResponse(results=search_results)


@router.post("/rebuild", response_model=dict)
async def rebuild_index(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Rebuild the search index for all notes
    """
    # Use default org_id
    org_id = "default"

    # Rebuild index
    count = await rebuild_index_for_org(org_id, db)

    return {"success": True, "indexed_notes": count}
