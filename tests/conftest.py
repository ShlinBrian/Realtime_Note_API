"""
Shared test configuration and fixtures
"""
import pytest
import asyncio
import uuid
import os
import tempfile
from typing import Generator, AsyncGenerator
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from api.main import app
from api.db.database import Base, get_db, get_async_db
from api.models.models import Organization, User, UserRole, Note, ApiKey
from api.auth.auth import get_current_user


# Test database URLs
SQLITE_TEST_URL = "sqlite:///:memory:"
ASYNC_SQLITE_TEST_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_engine():
    """Create test database engine"""
    engine = create_engine(
        SQLITE_TEST_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
async def async_test_engine():
    """Create async test database engine"""
    engine = create_async_engine(
        ASYNC_SQLITE_TEST_URL,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def test_session(test_engine):
    """Create test database session"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
async def async_test_session(async_test_engine):
    """Create async test database session"""
    async_session_local = async_sessionmaker(
        bind=async_test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session_local() as session:
        yield session


@pytest.fixture
def override_get_db(test_session):
    """Override database dependency for testing"""
    def _override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def override_get_async_db(async_test_session):
    """Override async database dependency for testing"""
    async def _override_get_async_db():
        yield async_test_session

    app.dependency_overrides[get_async_db] = _override_get_async_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def test_client(override_get_db):
    """Create test client with overridden dependencies"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_test_client(override_get_async_db):
    """Create async test client"""
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_org(test_session):
    """Create test organization"""
    org = Organization(
        org_id=str(uuid.uuid4()),
        name="Test Organization",
        quota_json={"limit": 1000}
    )
    test_session.add(org)
    test_session.commit()
    test_session.refresh(org)
    return org


@pytest.fixture
def test_user(test_session, test_org):
    """Create test user"""
    user = User(
        user_id=str(uuid.uuid4()),
        org_id=test_org.org_id,
        email="test@example.com",
        role=UserRole.ADMIN
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture
def test_api_key(test_session, test_org):
    """Create test API key"""
    api_key = ApiKey(
        key_id=str(uuid.uuid4()),
        org_id=test_org.org_id,
        hash="test_key_hash",
        name="Test API Key"
    )
    test_session.add(api_key)
    test_session.commit()
    test_session.refresh(api_key)
    return api_key


@pytest.fixture
def test_note(test_session, test_org):
    """Create test note"""
    note = Note(
        note_id=str(uuid.uuid4()),
        org_id=test_org.org_id,
        title="Test Note",
        content_md="# Test Note\n\nThis is a test note with some content.",
        version=1,
        deleted=False
    )
    test_session.add(note)
    test_session.commit()
    test_session.refresh(note)
    return note


@pytest.fixture
def auth_headers(test_api_key):
    """Create authentication headers for requests"""
    return {"x-api-key": f"rk_{test_api_key.hash}"}


@pytest.fixture
def mock_auth_user(test_user):
    """Mock authenticated user"""
    with patch.object(app.dependency_overrides, 'get', return_value=lambda: test_user):
        app.dependency_overrides[get_current_user] = lambda: test_user
        yield test_user
        app.dependency_overrides.clear()


@pytest.fixture
def mock_vector_search():
    """Mock vector search functionality"""
    with patch('api.search.vector_search.text_to_embedding') as mock_embedding, \
         patch('api.search.vector_search.index_note') as mock_index, \
         patch('api.search.vector_search.remove_note_from_index') as mock_remove, \
         patch('api.search.vector_search.search_notes') as mock_search:

        # Mock embedding returns a simple array
        mock_embedding.return_value = [0.1] * 384

        # Mock search returns test results
        mock_search.return_value = [
            ("test-note-id", 0.95),
            ("another-note-id", 0.75)
        ]

        yield {
            'embedding': mock_embedding,
            'index': mock_index,
            'remove': mock_remove,
            'search': mock_search
        }


@pytest.fixture
def temp_index_dir():
    """Create temporary directory for vector indices"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_dir = os.environ.get('INDEX_DIR')
        os.environ['INDEX_DIR'] = temp_dir

        # Clear any existing indices
        from api.search.vector_search import index_registry
        index_registry.clear()

        yield temp_dir

        # Clean up after test
        index_registry.clear()

        if original_dir:
            os.environ['INDEX_DIR'] = original_dir
        elif 'INDEX_DIR' in os.environ:
            del os.environ['INDEX_DIR']


@pytest.fixture
def mock_redis():
    """Mock Redis for rate limiting and caching"""
    mock_redis = Mock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.incr.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.publish.return_value = 1

    with patch('api.auth.rate_limit.redis_client', mock_redis):
        yield mock_redis


@pytest.fixture
def sample_notes_data():
    """Sample notes data for testing"""
    return [
        {
            "title": "Machine Learning Basics",
            "content_md": "# ML\n\nMachine learning is a subset of AI that focuses on algorithms.",
        },
        {
            "title": "Python Programming",
            "content_md": "# Python\n\nPython is a high-level programming language.",
        },
        {
            "title": "Data Science",
            "content_md": "# Data Science\n\nData science combines statistics and programming.",
        }
    ]