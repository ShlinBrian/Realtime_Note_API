from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional, Tuple
import time

from api.db.database import get_async_db, set_tenant_context
from api.models.models import Note, User
from api.models.schemas import (
    NoteCreate,
    NotePatch,
    NoteResponse,
    NoteDeleteResponse,
    UserRole,
)
from api.auth.auth import get_current_active_user, get_user_with_permission
from api.auth.rate_limit import check_rate_limit
from api.search.vector_search import index_note, remove_note_from_index

router = APIRouter(
    prefix="/v1/notes", tags=["notes"], dependencies=[Depends(check_rate_limit)]
)


@router.post("", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_note(
    note: NoteCreate,
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.EDITOR)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new note

    Requires editor role or higher
    """
    user, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

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
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.VIEWER)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get a note by ID

    Requires viewer role or higher
    """
    user, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

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
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.EDITOR)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update a note

    Requires editor role or higher
    """
    user, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

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
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.OWNER)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete a note

    Requires owner role or higher
    """
    user, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

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
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.VIEWER)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all notes for the organization

    Requires viewer role or higher
    """
    user, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

    # Get notes
    result = await db.execute(
        select(Note)
        .where(Note.org_id == org_id, Note.deleted == False)
        .offset(skip)
        .limit(limit)
        .order_by(Note.updated_at.desc())
    )
    notes = result.scalars().all()

    return notes
