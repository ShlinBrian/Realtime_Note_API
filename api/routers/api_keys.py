from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Tuple, Optional
from datetime import datetime

from api.db.database import get_async_db, set_tenant_context
from api.models.models import User, ApiKey
from api.models.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyInfo, UserRole
from api.auth.auth import (
    get_current_active_user,
    get_user_with_permission,
    generate_api_key,
    hash_api_key,
)
from api.auth.rate_limit import check_rate_limit

router = APIRouter(
    prefix="/v1/api-keys", tags=["api-keys"], dependencies=[Depends(check_rate_limit)]
)


@router.post("", response_model=ApiKeyResponse)
async def create_api_key(
    api_key_create: ApiKeyCreate,
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.OWNER)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new API key

    Requires owner role or higher
    """
    user, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

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
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.OWNER)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all API keys for the organization

    Requires owner role or higher
    """
    user, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

    # Get API keys
    result = await db.execute(select(ApiKey).where(ApiKey.org_id == org_id))
    api_keys = result.scalars().all()

    return api_keys


@router.delete("/{key_id}", response_model=dict)
async def delete_api_key(
    key_id: str,
    current_user: Tuple[User, str] = Depends(get_user_with_permission(UserRole.OWNER)),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete an API key

    Requires owner role or higher
    """
    user, org_id = current_user

    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

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
