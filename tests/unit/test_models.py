"""
Unit tests for database models
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from api.models.models import Organization, User, UserRole, Note, ApiKey


class TestOrganization:
    """Test Organization model"""

    def test_create_organization(self, test_session):
        """Test creating an organization"""
        org = Organization(
            org_id=str(uuid.uuid4()),
            name="Test Org",
            quota_json={"limit": 1000}
        )
        test_session.add(org)
        test_session.commit()

        assert org.org_id is not None
        assert org.name == "Test Org"
        assert org.quota_json == {"limit": 1000}
        assert org.created_at is not None
        # Organization doesn't have updated_at field

    def test_organization_repr(self, test_session):
        """Test organization string representation"""
        org = Organization(
            org_id=str(uuid.uuid4()),
            name="Test Org"
        )
        test_session.add(org)
        test_session.commit()

        # Organization model doesn't have custom __repr__, so check object representation
        repr_str = repr(org)
        assert "Organization" in repr_str
        assert "object at" in repr_str

    def test_organization_unique_constraint(self, test_session):
        """Test organization unique constraints"""
        org_id = str(uuid.uuid4())

        org1 = Organization(org_id=org_id, name="First Org")
        test_session.add(org1)
        test_session.commit()

        org2 = Organization(org_id=org_id, name="Second Org")
        test_session.add(org2)

        with pytest.raises(IntegrityError):
            test_session.commit()


class TestUser:
    """Test User model"""

    def test_create_user(self, test_session, test_org):
        """Test creating a user"""
        user = User(
            user_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            email="test@example.com",
            role=UserRole.ADMIN
        )
        test_session.add(user)
        test_session.commit()

        assert user.user_id is not None
        assert user.org_id == test_org.org_id
        assert user.email == "test@example.com"
        assert user.role == UserRole.ADMIN
        # User model doesn't have is_active field
        assert user.created_at is not None

    def test_user_role_enum(self, test_session, test_org):
        """Test user role enumeration"""
        admin_user = User(
            user_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            email="admin@example.com",
            role=UserRole.ADMIN
        )

        member_user = User(
            user_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            email="member@example.com",
            role=UserRole.EDITOR
        )

        test_session.add_all([admin_user, member_user])
        test_session.commit()

        assert admin_user.role == UserRole.ADMIN
        assert member_user.role == UserRole.EDITOR

    def test_user_email_not_unique_per_org(self, test_session, test_org):
        """Test that user email is not enforced as unique per organization in current schema"""
        user1 = User(
            user_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            email="duplicate@example.com",
            role=UserRole.ADMIN
        )
        test_session.add(user1)
        test_session.commit()

        user2 = User(
            user_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            email="duplicate@example.com",
            role=UserRole.EDITOR
        )
        test_session.add(user2)

        # Current schema allows duplicate emails within the same org
        test_session.commit()  # Should not raise

        assert user1.email == user2.email
        assert user1.org_id == user2.org_id


class TestNote:
    """Test Note model"""

    def test_create_note(self, test_session, test_org):
        """Test creating a note"""
        note = Note(
            note_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            title="Test Note",
            content_md="# Test\n\nThis is a test note.",
            version=1
        )
        test_session.add(note)
        test_session.commit()

        assert note.note_id is not None
        assert note.org_id == test_org.org_id
        assert note.title == "Test Note"
        assert note.content_md == "# Test\n\nThis is a test note."
        assert note.version == 1
        assert note.deleted is False
        assert note.created_at is not None
        assert note.updated_at is not None

    def test_note_soft_delete(self, test_session, test_org):
        """Test note soft deletion"""
        note = Note(
            note_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            title="To Delete",
            content_md="This will be deleted",
            version=1
        )
        test_session.add(note)
        test_session.commit()

        # Soft delete
        note.deleted = True
        test_session.commit()

        assert note.deleted is True

    def test_note_version_increment(self, test_session, test_org):
        """Test note version incrementing"""
        note = Note(
            note_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            title="Versioned Note",
            content_md="Original content",
            version=1
        )
        test_session.add(note)
        test_session.commit()

        # Update content and version
        note.content_md = "Updated content"
        note.version = 2
        test_session.commit()

        assert note.version == 2
        assert note.content_md == "Updated content"

    def test_note_empty_content(self, test_session, test_org):
        """Test note with empty content"""
        note = Note(
            note_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            title="Empty Note",
            content_md="",
            version=1
        )
        test_session.add(note)
        test_session.commit()

        assert note.content_md == ""
        assert note.title == "Empty Note"


class TestApiKey:
    """Test ApiKey model"""

    def test_create_api_key(self, test_session, test_org):
        """Test creating an API key"""
        api_key = ApiKey(
            key_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            hash="test_hash_123",
            name="Test API Key"
        )
        test_session.add(api_key)
        test_session.commit()

        assert api_key.key_id is not None
        assert api_key.org_id == test_org.org_id
        assert api_key.hash == "test_hash_123"
        assert api_key.name == "Test API Key"
        assert api_key.created_at is not None

    def test_api_key_deactivation(self, test_session, test_org):
        """Test API key modification (since no is_active field)"""
        api_key = ApiKey(
            key_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            hash="test_hash_456",
            name="Original Key"
        )
        test_session.add(api_key)
        test_session.commit()

        # Modify the key name to test updates
        original_name = api_key.name
        api_key.name = "Modified Key"
        test_session.commit()

        assert api_key.name == "Modified Key"
        assert api_key.name != original_name

    def test_api_key_unique_constraint(self, test_session, test_org):
        """Test API key unique constraints"""
        key_id = str(uuid.uuid4())

        key1 = ApiKey(
            key_id=key_id,
            org_id=test_org.org_id,
            hash="hash1",
            name="First Key"
        )
        test_session.add(key1)
        test_session.commit()

        key2 = ApiKey(
            key_id=key_id,
            org_id=test_org.org_id,
            hash="hash2",
            name="Second Key"
        )
        test_session.add(key2)

        with pytest.raises(IntegrityError):
            test_session.commit()


class TestModelRelationships:
    """Test relationships between models"""

    def test_organization_users_relationship(self, test_session, test_org):
        """Test organization to users relationship"""
        user1 = User(
            user_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            email="user1@example.com",
            role=UserRole.ADMIN
        )
        user2 = User(
            user_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            email="user2@example.com",
            role=UserRole.EDITOR
        )
        test_session.add_all([user1, user2])
        test_session.commit()

        # Test that we can access users through organization
        test_session.refresh(test_org)
        assert len(test_org.users) == 2
        assert user1 in test_org.users
        assert user2 in test_org.users

    def test_organization_notes_relationship(self, test_session, test_org):
        """Test organization to notes relationship"""
        note1 = Note(
            note_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            title="Note 1",
            content_md="Content 1",
            version=1
        )
        note2 = Note(
            note_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            title="Note 2",
            content_md="Content 2",
            version=1
        )
        test_session.add_all([note1, note2])
        test_session.commit()

        # Test that we can access notes through organization
        test_session.refresh(test_org)
        assert len(test_org.notes) == 2
        assert note1 in test_org.notes
        assert note2 in test_org.notes

    def test_cascade_delete_behavior(self, test_session, test_org):
        """Test cascade delete behavior"""
        # Add related objects
        user = User(
            user_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            email="test@example.com",
            role=UserRole.ADMIN
        )
        note = Note(
            note_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            title="Test Note",
            content_md="Test content",
            version=1
        )
        api_key = ApiKey(
            key_id=str(uuid.uuid4()),
            org_id=test_org.org_id,
            hash="test_hash",
            name="Test Key"
        )

        test_session.add_all([user, note, api_key])
        test_session.commit()

        # Verify objects exist
        assert test_session.query(User).filter_by(org_id=test_org.org_id).count() == 1
        assert test_session.query(Note).filter_by(org_id=test_org.org_id).count() == 1
        assert test_session.query(ApiKey).filter_by(org_id=test_org.org_id).count() == 1

        # Delete organization
        test_session.delete(test_org)

        # This will fail due to foreign key constraints since cascade delete is not configured
        with pytest.raises(IntegrityError):
            test_session.commit()

        # Rollback the failed transaction
        test_session.rollback()

        # Verify objects still exist after rollback
        assert test_session.query(User).filter_by(org_id=test_org.org_id).count() == 1
        assert test_session.query(Note).filter_by(org_id=test_org.org_id).count() == 1
        assert test_session.query(ApiKey).filter_by(org_id=test_org.org_id).count() == 1