from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from api.db.database import get_async_db
from api.models.models import Note
from api.models.schemas import (
    NoteCreate,
    NotePatch,
    NoteResponse,
    NoteDeleteResponse,
)
from api.search.vector_search import index_note, remove_note_from_index

router = APIRouter(prefix="/v1/notes", tags=["notes"])


@router.post("", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_note(
    note: NoteCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new note
    """
    # Create note with a default org_id
    org_id = "default"

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


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
):
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


@router.patch("/{note_id}", response_model=dict)
async def update_note(
    note_id: str,
    note_update: NotePatch,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update a note
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


@router.delete("/{note_id}", response_model=NoteDeleteResponse)
async def delete_note(
    note_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete a note
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


@router.get("", response_model=List[NoteResponse])
async def list_notes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all notes
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
