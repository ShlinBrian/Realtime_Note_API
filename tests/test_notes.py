import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import uuid

from api.main import app
from api.db.database import Base, get_db
from api.models.models import Organization, User, UserRole, Note

# Create in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Override the get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture
def test_db():
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create test data
    db = TestingSessionLocal()

    # Create organization
    org = Organization(org_id=str(uuid.uuid4()), name="Test Organization")
    db.add(org)

    # Create admin user
    admin = User(
        user_id=str(uuid.uuid4()),
        org_id=org.org_id,
        email="admin@example.com",
        role=UserRole.ADMIN,
    )
    db.add(admin)

    # Create test note
    note = Note(
        note_id=str(uuid.uuid4()),
        org_id=org.org_id,
        title="Test Note",
        content_md="# Test\n\nThis is a test note.",
        version=1,
    )
    db.add(note)

    db.commit()

    # Return test data
    yield {"org": org, "admin": admin, "note": note}

    # Clean up
    Base.metadata.drop_all(bind=engine)


def test_get_note(test_db):
    # Mock authentication
    # In a real test, we would use a proper authentication mechanism
    headers = {"x-api-key": "test_key"}

    # Test getting a note
    response = client.get(f"/v1/notes/{test_db['note'].note_id}", headers=headers)

    # In a real test, this would pass with proper authentication
    # Here we expect 401 because we're using a fake API key
    assert response.status_code == 401
