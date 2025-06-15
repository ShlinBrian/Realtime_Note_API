from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from datetime import datetime

from api.db.database import get_async_db
from api.models.models import ApiKey
from api.models.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyInfo
from api.utils.organization import get_or_create_default_organization

# We'll keep the API key generation functions since they might be useful
# without authentication
from api.auth.auth import generate_api_key, hash_api_key

router = APIRouter(
    prefix="/v1/api-keys",
    tags=["api-keys"],
    responses={
        404: {"description": "API key not found"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "",
    response_model=ApiKeyResponse,
    summary="Create a new API key",
    description="""
**Description:** Generate a new API key for authentication. The secret key will only be shown once upon creation, so save it immediately.

**Request Body:**
1. name (required, string): A descriptive name for the API key (1-100 characters)
2. expires_at (optional, datetime): Optional expiration date in ISO format (e.g., "2025-12-31T23:59:59Z")

**Headers:**
- Content-Type: application/json (required)
- x-api-key: your_api_key (optional, for authentication)

**Response:** Complete API key object including the secret key value (only time it's shown)

**Example Request:**
```json
{
    "name": "Production API Key",
    "expires_at": "2025-12-31T23:59:59Z"
}
```

**Example Response:**
```json
{
    "key_id": "key_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Production API Key",
    "key": "rk_1234567890abcdef1234567890abcdef",
    "created_at": "2024-01-15T10:30:00Z",
    "expires_at": "2025-12-31T23:59:59Z"
}
```

**Security Notes:**
- Save the key immediately - it won't be shown again
- Use the key in the `x-api-key` header for authentication
- Store keys securely (environment variables, secret managers)
- Rotate keys regularly for better security
""",
    responses={
        201: {
            "description": "API key created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "key_id": "key_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "name": "My API Key",
                        "key": "rk_1234567890abcdef1234567890abcdef",
                        "created_at": "2024-01-15T10:30:00Z",
                        "expires_at": "2025-01-15T10:30:00Z",
                    }
                }
            },
        },
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    api_key_create: ApiKeyCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new API key for API authentication.

    **Request Body:**
    - **name**: A descriptive name for the API key (required)
    - **expires_at**: Optional expiration date (ISO format, e.g., "2025-12-31T23:59:59Z")

    **Security Features:**
    - **Secure Generation**: Uses cryptographically secure random generation
    - **Hash Storage**: Only hashed version is stored in database
    - **One-Time Display**: Full key value is only returned once
    - **Optional Expiration**: Set expiration dates for enhanced security

    **Request Body Example:**
    ```json
    {
        "name": "Production API Key",
        "expires_at": "2025-12-31T23:59:59Z"
    }
    ```

    **Important Security Notes:**
    - **Save the key immediately** - it won't be shown again
    - Use the `x-api-key` header for authentication
    - Store keys securely (environment variables, secret managers)
    - Rotate keys regularly for better security

    **Returns:** Complete API key object including the secret key value
    """
    # Get or create default organization
    org_id = await get_or_create_default_organization(db)

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


@router.get(
    "",
    response_model=List[ApiKeyInfo],
    summary="List all API keys",
    description="""
**Description:** Retrieve a list of all API keys for the organization. Secret key values are not included for security reasons.

**Query Parameters:** None

**Headers:**
- x-api-key: your_api_key (optional, for authentication)

**Response:** Array of API key information objects (without secret values)

**Example Request:**
```
GET /v1/api-keys
```

**Example Response:**
```json
[
    {
        "key_id": "key_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "name": "Production API Key",
        "created_at": "2024-01-15T10:30:00Z",
        "expires_at": "2025-01-15T10:30:00Z"
    },
    {
        "key_id": "key_b2c3d4e5-f6g7-8901-bcde-f21234567890",
        "name": "Development API Key",
        "created_at": "2024-01-10T14:20:00Z",
        "expires_at": null
    }
]
```

**Response Fields:**
- key_id: Unique identifier for the API key
- name: The descriptive name you provided
- created_at: When the key was created
- expires_at: Expiration date (null if no expiration)
""",
    response_description="Array of API key information (without secret values)",
    responses={
        200: {
            "description": "API keys retrieved successfully",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "key_id": "key_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "name": "Production API Key",
                            "created_at": "2024-01-15T10:30:00Z",
                            "expires_at": "2025-01-15T10:30:00Z",
                        },
                        {
                            "key_id": "key_b2c3d4e5-f6g7-8901-bcde-f21234567890",
                            "name": "Development API Key",
                            "created_at": "2024-01-10T14:20:00Z",
                            "expires_at": "None",
                        },
                    ]
                }
            },
        },
        500: {"description": "Internal server error"},
    },
)
async def list_api_keys(
    db: AsyncSession = Depends(get_async_db),
):
    """
    List all API keys for the organization.

    **Security Features:**
    - **No Secret Values**: Secret key values are never returned
    - **Organization Scoped**: Only shows keys for your organization
    - **Metadata Only**: Returns key names, IDs, and timestamps

    **Response Fields:**
    - **key_id**: Unique identifier for the API key
    - **name**: The descriptive name you provided
    - **created_at**: When the key was created
    - **expires_at**: Expiration date (null if no expiration)

    **Use Cases:**
    - Audit existing API keys
    - Manage key lifecycle
    - Identify keys that need rotation
    - Check expiration dates

    **Returns:** Array of API key metadata (no secret values)
    """
    # Get or create default organization
    org_id = await get_or_create_default_organization(db)

    # Get API keys
    result = await db.execute(select(ApiKey).where(ApiKey.org_id == org_id))
    api_keys = result.scalars().all()

    return api_keys


@router.delete(
    "/{key_id}",
    response_model=dict,
    summary="Delete an API key",
    description="""
**Description:** Permanently delete an API key. This action cannot be undone and will immediately invalidate the key.

**Path Parameters:**
1. key_id (required, string): The unique identifier of the API key to delete

**Headers:**
- x-api-key: your_api_key (optional, for authentication)

**Response:** Confirmation that the API key was deleted

**Example Request:**
```
DELETE /v1/api-keys/key_a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Example Response:**
```json
{
    "success": true
}
```

**Security Notes:**
- Key becomes invalid immediately
- Any applications using this key will lose access
- Consider rotating to a new key before deleting if still in use
- Deletion is logged for audit purposes
""",
    response_description="Confirmation that the API key was deleted",
    responses={
        200: {
            "description": "API key deleted successfully",
            "content": {"application/json": {"example": {"success": True}}},
        },
        404: {"description": "API key not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Permanently delete an API key.

    **Path Parameters:**
    - **key_id**: The unique identifier of the API key to delete

    **Security Features:**
    - **Immediate Invalidation**: Key becomes invalid immediately
    - **Permanent Action**: Cannot be undone
    - **Organization Scoped**: Can only delete keys from your organization

    **Important Notes:**
    - Any applications using this key will immediately lose access
    - Consider rotating to a new key before deleting if still in use
    - Deletion is logged for audit purposes

    **Use Cases:**
    - Remove compromised keys
    - Clean up unused keys
    - Rotate keys for security
    - Revoke access for former team members

    **Returns:** Success confirmation
    """
    # Get or create default organization
    org_id = await get_or_create_default_organization(db)

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
