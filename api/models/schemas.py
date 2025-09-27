from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum


class UserRole(str, Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    OWNER = "owner"
    ADMIN = "admin"


class ErrorResponse(BaseModel):
    error: Dict[str, str]


# Organization schemas
class OrganizationBase(BaseModel):
    name: str


class OrganizationCreate(OrganizationBase):
    pass


class Organization(OrganizationBase):
    org_id: str
    created_at: datetime
    quota_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.VIEWER


class UserCreate(UserBase):
    org_id: str
    password: Optional[str] = None
    oauth_subject: Optional[str] = None


class User(UserBase):
    user_id: str
    org_id: str
    created_at: datetime
    oauth_subject: Optional[str] = None

    class Config:
        from_attributes = True


# API Key schemas
class ApiKeyCreate(BaseModel):
    """Request schema for creating a new API key"""

    name: str = Field(
        ...,
        description="Descriptive name for the API key",
        example="Production API Key",
        min_length=1,
        max_length=100,
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Optional expiration date for the API key (ISO format)",
        example="2025-12-31T23:59:59Z",
    )


class ApiKeyResponse(BaseModel):
    """Response schema when creating an API key (includes secret key)"""

    key_id: str = Field(..., description="Unique identifier for the API key")
    name: str = Field(..., description="Descriptive name of the API key")
    key: str = Field(..., description="The secret API key value (only shown once)")
    created_at: datetime = Field(..., description="When the API key was created")
    expires_at: Optional[datetime] = Field(
        None, description="When the API key expires (if set)"
    )


class ApiKeyInfo(BaseModel):
    """Response schema for API key information (without secret key)"""

    key_id: str = Field(..., description="Unique identifier for the API key")
    name: str = Field(..., description="Descriptive name of the API key")
    created_at: datetime = Field(..., description="When the API key was created")
    expires_at: Optional[datetime] = Field(
        None, description="When the API key expires (if set)"
    )

    class Config:
        from_attributes = True


# Note schemas
class NoteBase(BaseModel):
    """Base schema for note data"""

    title: str = Field(
        ...,
        description="The title of the note",
        example="My Important Note",
        min_length=1,
        max_length=200,
    )
    content_md: str = Field(
        ...,
        description="The note content in Markdown format",
        example="# Hello World\n\nThis is a **markdown** note.",
    )


class NoteCreate(NoteBase):
    """Request schema for creating a new note"""

    pass


class NotePatch(BaseModel):
    """Request schema for partially updating a note"""

    title: Optional[str] = Field(
        None,
        description="New title for the note",
        example="Updated Title",
        min_length=1,
        max_length=200,
    )
    content_md: Optional[str] = Field(
        None,
        description="New content for the note in Markdown format",
        example="# Updated Content\n\nThis note has been updated.",
    )


class Note(NoteBase):
    """Complete note schema with metadata"""

    note_id: str = Field(..., description="Unique identifier for the note")
    version: int = Field(
        ..., description="Version number for optimistic concurrency control", example=1
    )
    created_at: datetime = Field(..., description="When the note was created")
    updated_at: datetime = Field(..., description="When the note was last updated")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Ensure title is not empty, provide default if needed"""
        if not v or v.strip() == '':
            return 'Untitled Note'
        return v

    class Config:
        from_attributes = True


class NoteResponse(Note):
    """Response schema for note operations"""

    pass


class NoteDeleteResponse(BaseModel):
    """Response schema for note deletion"""

    deleted: bool = Field(True, description="Confirmation that the note was deleted")


# WebSocket schemas
class WebSocketPatch(BaseModel):
    """Schema for real-time note updates via WebSocket"""

    patch: str = Field(..., description="Base64 encoded JSON patch for jsonmerge")
    version: int = Field(..., description="Version number for conflict resolution")


# Search schemas
class SearchRequest(BaseModel):
    """Request schema for semantic search"""

    query: str = Field(
        ...,
        description="Search query text",
        example="meeting notes project timeline",
        min_length=1,
    )
    top_k: int = Field(
        10, description="Maximum number of results to return", ge=1, le=100, example=5
    )


class SearchResult(BaseModel):
    """Individual search result"""

    note_id: str = Field(..., description="Unique identifier of the matching note")
    similarity_score: float = Field(
        ...,
        description="Similarity score (-1.0 to 1.0, higher is more relevant)",
        ge=-1.0,
        le=1.0,
        example=0.85,
    )
    title: str = Field(..., description="Title of the matching note")
    snippet: str = Field(..., description="Content snippet from the matching note")
    highlighted_content: Optional[str] = Field(None, description="Highlighted content snippet")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class SearchResponse(BaseModel):
    """Response schema for search operations"""

    results: List[SearchResult] = Field(
        ..., description="Array of search results ordered by relevance"
    )


# Usage schemas
class UsageResponse(BaseModel):
    """Response schema for usage statistics"""

    period: date = Field(
        ..., description="Date for this usage summary", example="2024-01-15"
    )
    requests: int = Field(
        ..., description="Total number of API requests for this period", example=1250
    )
    bytes: int = Field(
        ...,
        description="Total bandwidth usage in bytes for this period",
        example=2048576,
    )
    cost_usd: Optional[str] = Field(
        None,
        description="Calculated cost in USD (if billing is enabled)",
        example="12.50",
    )


# Token schemas
class Token(BaseModel):
    """Response schema for authentication tokens"""

    access_token: str = Field(
        ..., description="The bearer token for API authentication"
    )
    token_type: str = Field(
        ..., description="Token type (always 'bearer')", example="bearer"
    )
    expires_in: int = Field(..., description="Token lifetime in seconds", example=1800)


class TokenData(BaseModel):
    """Internal token data for JWT processing"""

    user_id: Optional[str] = Field(None, description="User identifier from token")
    org_id: Optional[str] = Field(
        None, description="Organization identifier from token"
    )
    role: Optional[UserRole] = Field(None, description="User role from token")
    org_id: Optional[str] = None
    role: Optional[UserRole] = None
