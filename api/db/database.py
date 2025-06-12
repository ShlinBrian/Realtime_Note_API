from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import os
from typing import Generator, AsyncGenerator

# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost/notes"
)
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2", "postgresql+asyncpg")

# Create engine for synchronous operations (migrations, etc.)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create async engine for API operations
async_engine = create_async_engine(ASYNC_DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    class_=AsyncSession, autocommit=False, autoflush=False, bind=async_engine
)

# Base class for SQLAlchemy models
Base = declarative_base()


# Dependency for getting DB session
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Async dependency for getting DB session
async def get_async_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session
