from fastapi import Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import hashlib
import hmac
import secrets
import os
from typing import Optional, Tuple

from api.db.database import get_async_db, set_tenant_context
from api.models.models import User, ApiKey, UserRole, Organization
from api.models.schemas import TokenData, UserRole as SchemaUserRole

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
API_KEY_PREFIX = "rk_"

# Security utilities
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


# Password utilities
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


# API Key utilities
def generate_api_key():
    """Generate a random API key with the specified prefix"""
    random_bytes = secrets.token_bytes(24)
    key = API_KEY_PREFIX + secrets.token_urlsafe(32)
    return key


def hash_api_key(api_key: str) -> str:
    """Create a hash of the API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash"""
    return hmac.compare_digest(hash_api_key(api_key), stored_hash)


# JWT token utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user_from_token(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_async_db)
) -> Tuple[User, str]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.user_id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    # Set tenant context for RLS
    await set_tenant_context(db, user.org_id)

    return user, user.org_id


async def get_current_user_from_api_key(
    api_key: str = Security(api_key_header), db: AsyncSession = Depends(get_async_db)
) -> Tuple[Optional[User], str]:
    if not api_key:
        return None, ""

    # Query for the API key
    result = await db.execute(
        select(ApiKey).where(ApiKey.hash == hash_api_key(api_key))
    )
    db_api_key = result.scalar_one_or_none()

    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Check if the key is expired
    if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    # Set tenant context for RLS
    await set_tenant_context(db, db_api_key.org_id)

    # Get the organization's owner as the default user
    result = await db.execute(
        select(User)
        .where(User.org_id == db_api_key.org_id)
        .where(User.role == UserRole.OWNER)
        .limit(1)
    )
    user = result.scalar_one_or_none()

    return user, db_api_key.org_id


async def get_current_user(
    token_user: Tuple[Optional[User], str] = Depends(get_current_user_from_token),
    api_key_user: Tuple[Optional[User], str] = Depends(get_current_user_from_api_key),
) -> Tuple[User, str]:
    user, org_id = token_user if token_user[0] is not None else api_key_user

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user, org_id


async def get_current_active_user(
    current_user: Tuple[User, str] = Depends(get_current_user),
) -> Tuple[User, str]:
    user, org_id = current_user
    return user, org_id


def get_user_with_permission(required_role: SchemaUserRole):
    async def authorized_user(
        current_user: Tuple[User, str] = Depends(get_current_active_user),
    ) -> Tuple[User, str]:
        user, org_id = current_user

        # Convert DB role to schema role
        user_role = SchemaUserRole(user.role.value)

        # Role hierarchy: ADMIN > OWNER > EDITOR > VIEWER
        role_hierarchy = {
            SchemaUserRole.ADMIN: 4,
            SchemaUserRole.OWNER: 3,
            SchemaUserRole.EDITOR: 2,
            SchemaUserRole.VIEWER: 1,
        }

        if role_hierarchy[user_role] < role_hierarchy[required_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}",
            )

        return user, org_id

    return authorized_user
