from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, Dict, Any, Tuple
import httpx
import os
from datetime import datetime, timedelta

from api.db.database import get_async_db
from api.models.models import User, Organization, UserRole as DBUserRole
from api.models.schemas import Token, UserCreate, User as UserSchema
from api.auth.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    get_current_active_user,
)

# OAuth2 configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "notes-dev.auth0.com")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "your-client-id")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "your-client-secret")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "https://api.notes.example.com")

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get an access token using username/password
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # Validate user and password
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.user_id}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800,  # 30 minutes in seconds
    }


@router.post("/device/code", response_model=Dict[str, Any])
async def device_code():
    """
    Start OAuth 2.1 Device Code flow
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{AUTH0_DOMAIN}/oauth/device/code",
            data={
                "client_id": AUTH0_CLIENT_ID,
                "scope": "openid profile email",
                "audience": AUTH0_AUDIENCE,
            },
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start device code flow",
            )

        return response.json()


@router.post("/device/token", response_model=Token)
async def device_token(
    device_code: str = Form(...), db: AsyncSession = Depends(get_async_db)
):
    """
    Complete OAuth 2.1 Device Code flow and get access token
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
                "client_id": AUTH0_CLIENT_ID,
                "client_secret": AUTH0_CLIENT_SECRET,
            },
        )

        if response.status_code != 200:
            error_data = response.json()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_data.get("error_description", "Failed to get token"),
            )

        token_data = response.json()

        # Get user info from Auth0
        user_info_response = await client.get(
            f"https://{AUTH0_DOMAIN}/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )

        if user_info_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user info",
            )

        user_info = user_info_response.json()

        # Find or create user
        result = await db.execute(
            select(User).where(User.oauth_subject == user_info["sub"])
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            # First, check if organization exists based on email domain
            email = user_info.get("email", "")
            domain = email.split("@")[-1] if "@" in email else None

            if domain:
                # Look for organization with matching domain
                result = await db.execute(
                    select(Organization).where(Organization.domain == domain)
                )
                org = result.scalar_one_or_none()

                if not org:
                    # Create new organization
                    org = Organization(name=domain, domain=domain)
                    db.add(org)
                    await db.commit()
                    await db.refresh(org)

                # Create user in organization
                user = User(
                    email=email,
                    oauth_subject=user_info["sub"],
                    org_id=org.org_id,
                    role=DBUserRole.VIEWER,  # Default role
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email address",
                )

        # Create our own access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.user_id}, expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 1800,  # 30 minutes in seconds
        }


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: Tuple[User, str] = Depends(get_current_active_user),
):
    """
    Get information about the current user
    """
    user, _ = current_user
    return user
