from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/token")
async def login_for_access_token():
    """
    Dummy endpoint that always returns a successful response
    """
    return {
        "access_token": "dummy_token",
        "token_type": "bearer",
        "expires_in": 1800,  # 30 minutes in seconds
    }


@router.post("/device/code", response_model=Dict[str, Any])
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


@router.post("/device/token")
async def device_token():
    """
    Dummy endpoint for OAuth 2.1 Device Code flow token
    """
    return {
        "access_token": "dummy_token",
        "token_type": "bearer",
        "expires_in": 1800,  # 30 minutes in seconds
    }


@router.get("/me")
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
