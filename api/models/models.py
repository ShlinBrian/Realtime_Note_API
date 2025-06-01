from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    Boolean,
    DateTime,
    Date,
    JSON,
    Enum,
    Text,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from api.db.database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class UserRole(enum.Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    OWNER = "owner"
    ADMIN = "admin"


class Organization(Base):
    __tablename__ = "org"

    org_id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    quota_json = Column(JSONB, nullable=True)

    users = relationship("User", back_populates="organization")
    api_keys = relationship("ApiKey", back_populates="organization")
    notes = relationship("Note", back_populates="organization")


class User(Base):
    __tablename__ = "user"

    user_id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("org.org_id"), nullable=False)
    email = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.VIEWER)
    oauth_subject = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="users")
    usage_logs = relationship("UsageLog", back_populates="user")


class ApiKey(Base):
    __tablename__ = "api_key"

    key_id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("org.org_id"), nullable=False)
    hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="api_keys")


class Note(Base):
    __tablename__ = "note"

    note_id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("org.org_id"), nullable=False)
    title = Column(String, nullable=False)
    content_md = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted = Column(Boolean, default=False)

    organization = relationship("Organization", back_populates="notes")

    __table_args__ = {
        # RLS policy for tenant isolation
        "info": {
            "rls_policy": "CREATE POLICY org_isolation ON note USING (org_id = current_setting('app.org_id')::text)"
        }
    }


class UsageLog(Base):
    __tablename__ = "usage_log"

    log_id = Column(String, primary_key=True, default=generate_uuid)
    org_id = Column(String, ForeignKey("org.org_id"), nullable=False)
    user_id = Column(String, ForeignKey("user.user_id"), nullable=True)
    kind = Column(String, nullable=False)  # REST, WS, gRPC
    endpoint = Column(String, nullable=False)
    bytes = Column(Integer, nullable=False, default=0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization")
    user = relationship("User", back_populates="usage_logs")


class UsageSummary(Base):
    __tablename__ = "usage_summary"

    org_id = Column(String, ForeignKey("org.org_id"), primary_key=True)
    period = Column(Date, primary_key=True)
    requests = Column(Integer, nullable=False, default=0)
    bytes = Column(Integer, nullable=False, default=0)
    invoice_json = Column(JSONB, nullable=True)

    organization = relationship("Organization")


class SwaggerAcl(Base):
    __tablename__ = "swagger_acl"

    role = Column(Enum(UserRole), primary_key=True)
    tag = Column(String, primary_key=True)
    can_read = Column(Boolean, nullable=False, default=False)
    can_write = Column(Boolean, nullable=False, default=False)
