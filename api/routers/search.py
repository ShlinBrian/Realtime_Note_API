from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple

from api.db.database import get_async_db, set_tenant_context
from api.models.models import Note, User
from api.models.schemas import SearchRequest, SearchResponse, SearchResult, UserRole
from api.auth.auth import get_current_active_user, get_user_with_permission
from api.auth.rate_limit import check_rate_limit
from api.search.vector_search import search_notes, rebuild_index_for_org

router = APIRouter(
    prefix="/v1/search", tags=["search"], dependencies=[Depends(check_rate_limit)]
)


@router.post("", response_model=SearchResponse)
async def search(
    search_request: SearchRequest,
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.VIEWER)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Search for notes using vector similarity

    Requires viewer role or higher
    """
    user, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

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
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Rebuild the search index for the organization

    Requires admin role
    """
    user, org_id = current_user

    # Rebuild index
    count = await rebuild_index_for_org(org_id, db)

    return {"success": True, "indexed_notes": count}
