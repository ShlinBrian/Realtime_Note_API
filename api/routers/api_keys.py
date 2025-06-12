from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from datetime import datetime

from api.db.database import get_async_db
from api.models.models import ApiKey
from api.models.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyInfo

# We'll keep the API key generation functions since they might be useful
# without authentication
from api.auth.auth import generate_api_key, hash_api_key

router = APIRouter(prefix="/v1/api-keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyResponse)
async def create_api_key(
    api_key_create: ApiKeyCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new API key
    """
    # Use default org_id
    org_id = "default"

    # Generate API key
    key = generate_api_key()

    # Create API key record
    db_api_key = ApiKey(
        org_id=org_id,
        name=api_key_create.name,
        hash=hash_api_key(key),
        expires_at=api_key_create.expires_at,
    )

    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)

    # Return API key (only time it's returned in full)
    return ApiKeyResponse(
        key_id=db_api_key.key_id,
        name=db_api_key.name,
        key=key,
        created_at=db_api_key.created_at,
        expires_at=db_api_key.expires_at,
    )


@router.get("", response_model=List[ApiKeyInfo])
async def list_api_keys(
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all API keys
    """
    # Use default org_id
    org_id = "default"

    # Get API keys
    result = await db.execute(select(ApiKey).where(ApiKey.org_id == org_id))
    api_keys = result.scalars().all()

    return api_keys


@router.delete("/{key_id}", response_model=dict)
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete an API key
    """
    # Use default org_id
    org_id = "default"

    # Get API key
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_id == key_id, ApiKey.org_id == org_id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key with ID {key_id} not found",
        )

    # Delete API key
    await db.delete(api_key)
    await db.commit()

    return {"success": True}
