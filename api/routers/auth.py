from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

router = APIRouter(
    prefix="/v1/auth",
    tags=["auth"],
    responses={
        401: {"description": "Authentication failed"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "/token",
    summary="Get access token",
    description="""
**Description:** Obtain an access token for API authentication. Currently returns a dummy token for demo purposes.

**Request Body:** None (currently demo endpoint)

**Headers:**
- Content-Type: application/json (if body provided)

**Response:** Bearer token for API authentication

**Example Request:**
```
POST /v1/auth/token
```

**Example Response:**
```json
{
    "access_token": "dummy_token",
    "token_type": "bearer", 
    "expires_in": 1800
}
```

**Response Fields:**
- access_token: The bearer token for API requests
- token_type: Always "bearer"
- expires_in: Token lifetime in seconds (30 minutes)

**Usage:**
Use the returned token in the Authorization header:
```
Authorization: Bearer <access_token>
```

**Note:** This is currently a demo implementation that returns mock tokens.
""",
    response_description="Bearer token for API authentication",
    responses={
        200: {
            "description": "Token generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "dummy_token",
                        "token_type": "bearer",
                        "expires_in": 1800,
                    }
                }
            },
        },
        400: {"description": "Invalid credentials"},
        500: {"description": "Internal server error"},
    },
)
async def login_for_access_token():
    """
    Obtain an access token for API authentication.

    **Demo Implementation:**
    This is currently a dummy endpoint that returns a mock token for demonstration purposes.

    **In Production:**
    - Would validate user credentials
    - Generate real JWT tokens
    - Support multiple authentication methods
    - Implement proper token expiration

    **Response Fields:**
    - **access_token**: The bearer token for API requests
    - **token_type**: Always "bearer"
    - **expires_in**: Token lifetime in seconds (30 minutes)

    **Usage:**
    Use the returned token in the `Authorization` header:
    `Authorization: Bearer <access_token>`

    **Returns:** Bearer token for API authentication
    """
    return {
        "access_token": "dummy_token",
        "token_type": "bearer",
        "expires_in": 1800,  # 30 minutes in seconds
    }


@router.post(
    "/device/code",
    response_model=Dict[str, Any],
    summary="Start OAuth 2.1 Device Code flow",
    description="""
**Description:** Initiate OAuth 2.1 Device Code authorization flow. Returns a device code and user code for device authentication.

**Request Body:** None

**Headers:**
- Content-Type: application/json (if body provided)

**Response:** Device authorization information

**Example Request:**
```
POST /v1/auth/device/code
```

**Example Response:**
```json
{
    "device_code": "dummy_device_code",
    "user_code": "ABCD-1234",
    "verification_uri": "https://example.com/verify",
    "expires_in": 1800,
    "interval": 5
}
```

**Response Fields:**
- device_code: Code for the device to poll for authorization
- user_code: Short code for user to enter on verification page
- verification_uri: URL where user should go to authorize
- expires_in: How long the codes are valid (seconds)
- interval: How often to poll for authorization (seconds)

**Note:** This is currently a demo implementation.
""",
)
async def device_code():
    """
    Dummy endpoint for OAuth 2.1 Device Code flow
    """
    return {
        "device_code": "dummy_device_code",
        "user_code": "ABCD-1234",
        "verification_uri": "https://example.com/verify",
        "expires_in": 1800,
        "interval": 5,
    }


@router.post(
    "/device/token",
    summary="Exchange device code for token",
    description="""
**Description:** Exchange a device code for an access token in OAuth 2.1 Device Code flow. Poll this endpoint until authorization is complete.

**Request Body:** None (currently demo endpoint)

**Headers:**
- Content-Type: application/json (if body provided)

**Response:** Access token once user has authorized the device

**Example Request:**
```
POST /v1/auth/device/token
```

**Example Response:**
```json
{
    "access_token": "dummy_token",
    "token_type": "bearer",
    "expires_in": 1800
}
```

**Response Fields:**
- access_token: The bearer token for API requests
- token_type: Always "bearer"
- expires_in: Token lifetime in seconds (30 minutes)

**Polling Behavior:**
- Poll this endpoint at the interval specified in device/code response
- Continue until you receive a token or the codes expire
- Use exponential backoff if polling too frequently

**Note:** This is currently a demo implementation.
""",
)
async def device_token():
    """
    Dummy endpoint for OAuth 2.1 Device Code flow token
    """
    return {
        "access_token": "dummy_token",
        "token_type": "bearer",
        "expires_in": 1800,  # 30 minutes in seconds
    }


@router.get(
    "/me",
    summary="Get current user information",
    description="""
**Description:** Retrieve information about the currently authenticated user. Returns user profile and organization details.

**Query Parameters:** None

**Headers:**
- Authorization: Bearer <access_token> (optional, for authentication)
- x-api-key: your_api_key (optional, alternative authentication)

**Response:** Current user profile information

**Example Request:**
```
GET /v1/auth/me
Authorization: Bearer your_access_token
```

**Example Response:**
```json
{
    "user_id": "default_user",
    "email": "user@example.com",
    "role": "admin",
    "org_id": "default",
    "created_at": "2023-01-01T00:00:00Z"
}
```

**Response Fields:**
- user_id: Unique identifier for the user
- email: User's email address
- role: User's role (viewer, editor, owner, admin)
- org_id: Organization the user belongs to
- created_at: When the user account was created

**Use Cases:**
- Display user profile information
- Check user permissions and role
- Verify authentication status
- Get organization context

**Note:** This is currently a demo implementation returning mock data.
""",
)
async def get_current_user_info():
    """
    Return dummy user info
    """
    return {
        "user_id": "default_user",
        "email": "user@example.com",
        "role": "admin",
        "org_id": "default",
        "created_at": "2023-01-01T00:00:00Z",
    }
