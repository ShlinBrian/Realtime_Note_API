from pydantic import BaseModel, Field, EmailStr
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
    name: str
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    key_id: str
    name: str
    key: str  # Full key, only returned once
    created_at: datetime
    expires_at: Optional[datetime] = None


class ApiKeyInfo(BaseModel):
    key_id: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Note schemas
class NoteBase(BaseModel):
    title: str
    content_md: str


class NoteCreate(NoteBase):
    pass


class NotePatch(BaseModel):
    title: Optional[str] = None
    content_md: Optional[str] = None


class Note(NoteBase):
    note_id: str
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NoteResponse(Note):
    pass


class NoteDeleteResponse(BaseModel):
    deleted: bool = True


# WebSocket schemas
class WebSocketPatch(BaseModel):
    patch: str  # Base64 encoded JSON patch for jsonmerge
    version: int


# Search schemas
class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


class SearchResult(BaseModel):
    note_id: str
    score: float


class SearchResponse(BaseModel):
    results: List[SearchResult]


# Usage schemas
class UsageResponse(BaseModel):
    period: date
    requests: int
    bytes: int
    cost_usd: Optional[str] = None


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    user_id: Optional[str] = None
    org_id: Optional[str] = None
    role: Optional[UserRole] = None
