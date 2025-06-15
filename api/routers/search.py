from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from api.db.database import get_async_db
from api.models.models import Note
from api.models.schemas import SearchRequest, SearchResponse, SearchResult
from api.search.vector_search import search_notes, rebuild_index_for_org
from api.utils.organization import get_or_create_default_organization

router = APIRouter(
    prefix="/v1/search",
    tags=["search"],
    responses={
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "",
    response_model=SearchResponse,
    summary="Search notes using semantic similarity",
    description="""
**Description:** Search through all notes using vector-based semantic similarity. Finds notes based on meaning and context, not just keyword matching.

**Request Body:**
1. query (required, string): The search query text to find similar notes
2. top_k (optional, integer): Maximum number of results to return (default: 10, range: 1-100)

**Headers:**
- Content-Type: application/json (required)
- x-api-key: your_api_key (optional, for authentication)

**Response:** Array of search results with note IDs and similarity scores

**Example Request:**
```json
{
    "query": "machine learning algorithms and neural networks",
    "top_k": 5
}
```

**Example Response:**
```json
{
    "results": [
        {
            "note_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "score": 0.95
        },
        {
            "note_id": "b2c3d4e5-f6g7-8901-bcde-f21234567890", 
            "score": 0.87
        }
    ]
}
```

**Score Explanation:**
- Scores range from 0.0 to 1.0
- Higher scores indicate better semantic matches
- Scores above 0.8 are typically very relevant
- Uses FAISS vector similarity for performance
""",
    responses={
        200: {
            "description": "Search completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "note_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "score": 0.95,
                            },
                            {
                                "note_id": "b2c3d4e5-f6g7-8901-bcde-f21234567890",
                                "score": 0.87,
                            },
                        ]
                    }
                }
            },
        },
        400: {"description": "Invalid search query"},
        500: {"description": "Search service error"},
    },
)
async def search(
    search_request: SearchRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Search for notes using advanced semantic similarity.

    **Request Body:**
    - **query**: The search query text (what you're looking for)
    - **top_k**: Maximum number of results to return (1-100, default: 10)

    **Search Features:**
    - **Semantic Search**: Finds notes by meaning, not just keywords
    - **Vector Similarity**: Uses FAISS for high-performance similarity search
    - **Ranked Results**: Results ordered by relevance (similarity score)
    - **Organization Scoped**: Only searches within your organization

    **How it works:**
    1. Query text is converted to a vector embedding
    2. Vector similarity is computed against all indexed notes
    3. Most similar notes are returned with scores
    4. Higher scores (closer to 1.0) indicate better matches

    **Request Body Example:**
    ```json
    {
        "query": "meeting notes project timeline",
        "top_k": 5
    }
    ```

    **Use Cases:**
    - Find related notes by topic
    - Discover relevant content you've forgotten about
    - Research across your knowledge base
    - Find notes that mention similar concepts

    **Returns:** List of note IDs with similarity scores (0.0 to 1.0)
    """
    # Get or create default organization
    org_id = await get_or_create_default_organization(db)

    # Search for notes
    results = await search_notes(
        query=search_request.query, org_id=org_id, top_k=search_request.top_k, db=db
    )

    # Format results
    search_results = [
        SearchResult(note_id=note_id, score=score) for note_id, score in results
    ]

    return SearchResponse(results=search_results)


@router.post(
    "/rebuild",
    response_model=dict,
    summary="Rebuild search index",
    description="Rebuild the entire search index for all notes. This is typically used for maintenance or after bulk data changes.",
    response_description="Status of the rebuild operation with count of indexed notes",
    responses={
        200: {
            "description": "Index rebuilt successfully",
            "content": {
                "application/json": {"example": {"success": True, "indexed_notes": 45}}
            },
        },
        500: {"description": "Index rebuild failed"},
    },
)
async def rebuild_index(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Rebuild the entire search index for all notes.

    **Administrative Operation:**
    This endpoint rebuilds the vector search index from scratch by:
    1. Clearing the existing index
    2. Re-processing all non-deleted notes
    3. Generating fresh vector embeddings
    4. Building a new optimized search index

    **When to use:**
    - After bulk note imports or updates
    - When search results seem inconsistent
    - During system maintenance
    - After changing embedding models (in production)

    **Performance Note:**
    - This operation can take time with many notes
    - Search functionality remains available during rebuild
    - New index replaces old one atomically when complete

    **Returns:** Success status and count of notes that were indexed
    """
    # Get or create default organization
    org_id = await get_or_create_default_organization(db)

    # Rebuild index
    count = await rebuild_index_for_org(org_id, db)

    return {"success": True, "indexed_notes": count}
