from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Response,
    Request,
    Query,
    Path,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from api.db.database import get_async_db
from api.models.models import Note, Organization
from api.models.schemas import (
    NoteCreate,
    NotePatch,
    NoteResponse,
    NoteDeleteResponse,
)
from api.search.vector_search import index_note, remove_note_from_index
from api.utils.organization import get_or_create_default_organization

router = APIRouter(
    prefix="/v1/notes",
    tags=["notes"],
    responses={
        404: {"description": "Note not found"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "",
    response_model=str,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new note",
    description="""
**Description:** Create a new Markdown note with a title and content. The note will be automatically indexed for semantic search and assigned a unique ID.

**Request Body:**
1. title (required, string): The title of the note (1-200 characters)
2. content_md (required, string): The note content in Markdown format

**Headers:**
- Content-Type: application/json (required)
- x-api-key: your_api_key (optional, for authentication)

**Response:** Returns the unique note ID as a string

**Example Request:**
```json
{
    "title": "My First Note",
    "content_md": "# Hello World\\n\\nThis is my first note with **markdown** formatting."
}
```

**Example Response:**
```
"a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```
""",
    responses={
        201: {
            "description": "Note created successfully",
            "content": {
                "application/json": {"example": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
            },
        },
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"},
    },
)
async def create_note(
    note: NoteCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new note with the following features:

    - **Title**: A descriptive title for the note (required)
    - **Content**: Markdown-formatted content (required)
    - **Automatic Indexing**: The note is automatically indexed for semantic search
    - **Version Control**: Notes start at version 1 and increment with each update
    - **Organization Scoped**: Notes are scoped to the default organization

    **Request Body Example:**
    ```json
    {
        "title": "My First Note",
        "content_md": "# Hello World\\n\\nThis is my first note with **markdown** formatting."
    }
    ```

    **Returns:** The unique note ID as a string
    """
    # Get or create default organization
    org_id = await get_or_create_default_organization(db)

    # Create note
    db_note = Note(
        title=note.title, content_md=note.content_md, org_id=org_id, version=1
    )

    db.add(db_note)
    await db.commit()
    await db.refresh(db_note)

    # Index for search
    await index_note(db_note)

    return db_note.note_id


@router.get(
    "/{note_id}",
    response_model=NoteResponse,
    summary="Get a note by ID",
    description="""
**Description:** Retrieve a specific note by its unique identifier. Returns the complete note with title, content, and metadata including version information for real-time collaboration.

**Path Parameters:**
1. note_id (required, string): The UUID of the note to retrieve

**Headers:**
- x-api-key: your_api_key (optional, for authentication)
- If-None-Match: W/"version_number" (optional, for conditional requests)

**Response:** Complete note object with metadata

**Example Request:**
```
GET /v1/notes/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Example Response:**
```json
{
    "note_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "My First Note",
    "content_md": "# Hello World\\n\\nThis is my first note.",
    "version": 1,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

**Response Headers:**
- ETag: W/"version_number" (for caching and conflict detection)
""",
    responses={
        200: {
            "description": "Note retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "note_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "title": "My First Note",
                        "content_md": "# Hello World\n\nThis is my first note.",
                        "version": 1,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        304: {"description": "Not modified (when using If-None-Match)"},
        404: {"description": "Note not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_note(
    note_id: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve a specific note by its unique identifier.

    **Path Parameters:**
    - **note_id**: The UUID of the note to retrieve (e.g., a1b2c3d4-e5f6-7890-abcd-ef1234567890)

    **Response includes:**
    - Complete note content in Markdown format
    - Metadata (creation time, last update, version)
    - Version number for conflict detection in real-time editing

    **Use Cases:**
    - Display a note for reading or editing
    - Get current version for real-time collaboration
    - Retrieve note metadata for management purposes
    """
    """
    Get a note by ID
    """
    # Get note
    result = await db.execute(
        select(Note).where(Note.note_id == note_id, Note.deleted == False)
    )
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    # Set ETag for caching
    response.headers["ETag"] = f'W/"{note.version}"'

    # Check If-None-Match header for conditional GET
    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match == f'W/"{note.version}"':
        response.status_code = status.HTTP_304_NOT_MODIFIED
        return None

    return note


@router.patch(
    "/{note_id}",
    response_model=dict,
    summary="Update a note",
    description="""
**Description:** Update the title and/or content of an existing note. Only provided fields will be updated. Version number automatically increments and the note is re-indexed for search.

**Path Parameters:**
1. note_id (required, string): The UUID of the note to update

**Request Body (all fields optional):**
1. title (optional, string): New title for the note (1-200 characters)
2. content_md (optional, string): New Markdown content for the note

**Headers:**
- Content-Type: application/json (required)
- x-api-key: your_api_key (optional, for authentication)

**Response:** Object containing the new version number

**Example Request:**
```json
{
    "title": "Updated Title",
    "content_md": "# Updated Content\\n\\nThis note has been updated."
}
```

**Example Response:**
```json
{
    "version": 2
}
```
""",
    responses={
        200: {
            "description": "Note updated successfully",
            "content": {"application/json": {"example": {"version": 2}}},
        },
        404: {"description": "Note not found"},
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"},
    },
)
async def update_note(
    note_id: str,
    note_update: NotePatch,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update an existing note with partial updates.

    **Path Parameters:**
    - **note_id**: The UUID of the note to update

    **Request Body** (all fields optional):
    - **title**: New title for the note
    - **content_md**: New Markdown content for the note

    **Features:**
    - **Partial Updates**: Only specify the fields you want to change
    - **Version Increment**: Version number automatically increments
    - **Search Re-indexing**: Updated notes are automatically re-indexed
    - **Optimistic Concurrency**: Version numbers help detect conflicts

    **Request Body Example:**
    ```json
    {
        "title": "Updated Title",
        "content_md": "# Updated Content\\n\\nThis note has been updated."
    }
    ```

    **Returns:** Object with the new version number
    """
    # Get note
    result = await db.execute(
        select(Note).where(Note.note_id == note_id, Note.deleted == False)
    )
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    # Update fields if provided
    update_needed = False

    if note_update.title is not None:
        note.title = note_update.title
        update_needed = True

    if note_update.content_md is not None:
        note.content_md = note_update.content_md
        update_needed = True

    if update_needed:
        # Increment version
        note.version += 1

        # Update note
        db.add(note)
        await db.commit()
        await db.refresh(note)

        # Update search index
        await index_note(note)

    return {"version": note.version}


@router.delete(
    "/{note_id}",
    response_model=NoteDeleteResponse,
    summary="Delete a note",
    description="""
**Description:** Soft delete a note by marking it as deleted. The note will be removed from search results and listing but data is preserved for potential recovery.

**Path Parameters:**
1. note_id (required, string): The UUID of the note to delete

**Headers:**
- x-api-key: your_api_key (optional, for authentication)

**Response:** Confirmation that the note was deleted

**Example Request:**
```
DELETE /v1/notes/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Example Response:**
```json
{
    "deleted": true
}
```
""",
    responses={
        200: {
            "description": "Note deleted successfully",
            "content": {"application/json": {"example": {"deleted": True}}},
        },
        404: {"description": "Note not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_note(
    note_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete a note using soft deletion.

    **Path Parameters:**
    - **note_id**: The UUID of the note to delete

    **Behavior:**
    - **Soft Delete**: Note is marked as deleted, not permanently removed
    - **Search Removal**: Note is removed from search index immediately
    - **Data Retention**: Note data is preserved for potential recovery
    - **Immediate Effect**: Note disappears from listings and search results

    **Use Cases:**
    - Remove unwanted notes
    - Clean up workspace
    - Accidentally deleted notes can potentially be recovered (with admin access)

    **Returns:** Confirmation object with `deleted: true`
    """
    # Get note
    result = await db.execute(
        select(Note).where(Note.note_id == note_id, Note.deleted == False)
    )
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    # Soft delete
    note.deleted = True
    db.add(note)
    await db.commit()

    # Remove from search index
    await remove_note_from_index(note)

    return {"deleted": True}


@router.get(
    "",
    response_model=List[NoteResponse],
    summary="List all notes",
    description="""
**Description:** Retrieve a paginated list of all notes, ordered by last update time (newest first). Only returns non-deleted notes.

**Query Parameters:**
1. skip (optional, integer): Number of notes to skip for pagination (default: 0, minimum: 0)
2. limit (optional, integer): Maximum number of notes to return (default: 100, range: 1-1000)

**Headers:**
- x-api-key: your_api_key (optional, for authentication)

**Response:** Array of note objects with complete metadata

**Example Request:**
```
GET /v1/notes?skip=0&limit=10
```

**Example Response:**
```json
[
    {
        "note_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "title": "My First Note",
        "content_md": "# Hello World\\n\\nThis is my first note.",
        "version": 1,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    },
    {
        "note_id": "b2c3d4e5-f6g7-8901-bcde-f21234567890",
        "title": "Second Note", 
        "content_md": "# Meeting Notes\\n\\n- Discussed project timeline",
        "version": 2,
        "created_at": "2024-01-14T09:15:00Z",
        "updated_at": "2024-01-15T11:45:00Z"
    }
]
```

**Pagination Examples:**
- First page: `?skip=0&limit=10`
- Second page: `?skip=10&limit=10`
- Third page: `?skip=20&limit=10`
""",
    responses={
        200: {
            "description": "Notes retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "note_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "title": "My First Note",
                            "content_md": "# Hello World\n\nThis is my first note.",
                            "version": 1,
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": "2024-01-15T10:30:00Z",
                        }
                    ]
                }
            },
        },
        500: {"description": "Internal server error"},
    },
)
async def list_notes(
    skip: int = Query(
        0, ge=0, description="Number of notes to skip for pagination", example=0
    ),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of notes to return", example=10
    ),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve a paginated list of all notes.

    **Query Parameters:**
    - **skip**: Number of notes to skip (for pagination, default: 0)
    - **limit**: Maximum number of notes to return (1-1000, default: 100)

    **Features:**
    - **Pagination**: Use skip and limit for efficient pagination
    - **Ordering**: Notes are ordered by last update time (newest first)
    - **Filtering**: Only returns non-deleted notes
    - **Complete Data**: Returns full note content and metadata

    **Pagination Example:**
    - First page: `?skip=0&limit=10`
    - Second page: `?skip=10&limit=10`
    - Third page: `?skip=20&limit=10`

    **Use Cases:**
    - Display notes in a dashboard
    - Browse all available notes
    - Implement infinite scroll or pagination
    - Export or backup notes

    **Returns:** Array of note objects, newest first
    """
    # Get notes
    result = await db.execute(
        select(Note)
        .where(Note.deleted == False)
        .offset(skip)
        .limit(limit)
        .order_by(Note.updated_at.desc())
    )
    notes = result.scalars().all()

    return notes
