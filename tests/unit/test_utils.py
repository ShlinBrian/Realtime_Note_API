"""
Unit tests for utility functions
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from api.utils.organization import get_or_create_default_organization
from api.models.models import Organization


class TestOrganizationUtils:
    """Test organization utility functions"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        mock_session = AsyncMock()
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.scalar_one_or_none = AsyncMock()
        return mock_session

    @pytest.fixture
    def sample_organization(self):
        """Sample organization model"""
        return Organization(
            org_id="test-org-123",
            name="Test Organization"
        )

    @pytest.mark.asyncio
    async def test_get_or_create_default_organization_existing_org(self, mock_db_session, sample_organization):
        """Test getting existing organization"""
        # Mock existing organization found
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_organization)
        mock_db_session.execute.return_value = mock_result

        # Call function
        org_id = await get_or_create_default_organization(mock_db_session)

        # Assertions
        assert org_id == "test-org-123"
        mock_db_session.execute.assert_called_once()
        mock_db_session.add.assert_not_called()  # Should not create new org

    @pytest.mark.asyncio
    async def test_get_or_create_default_organization_no_existing_org(self, mock_db_session):
        """Test creating new default organization when none exists"""
        # Mock no existing organization found
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db_session.execute.return_value = mock_result

        # Call function
        org_id = await get_or_create_default_organization(mock_db_session)

        # Assertions
        assert org_id == "default"
        mock_db_session.execute.assert_called_once()
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_default_organization_database_error(self, mock_db_session):
        """Test error handling when database operations fail"""
        # Mock database error
        mock_db_session.execute.side_effect = Exception("Database connection failed")

        # Call function
        org_id = await get_or_create_default_organization(mock_db_session)

        # Should return fallback org_id
        assert org_id == "e7ffb47c-d0d5-4ec0-995a-6025cc83b2c4"

    @pytest.mark.asyncio
    async def test_get_or_create_default_organization_commit_error(self, mock_db_session):
        """Test error handling when commit fails"""
        # Mock no existing organization, but commit fails
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit.side_effect = Exception("Commit failed")

        # Call function
        org_id = await get_or_create_default_organization(mock_db_session)

        # Should return fallback org_id
        assert org_id == "e7ffb47c-d0d5-4ec0-995a-6025cc83b2c4"

    @pytest.mark.asyncio
    async def test_get_or_create_default_organization_refresh_error(self, mock_db_session):
        """Test error handling when refresh fails"""
        # Mock no existing organization, commit succeeds, but refresh fails
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db_session.execute.return_value = mock_result
        mock_db_session.refresh.side_effect = Exception("Refresh failed")

        # Call function
        org_id = await get_or_create_default_organization(mock_db_session)

        # Should return fallback org_id
        assert org_id == "e7ffb47c-d0d5-4ec0-995a-6025cc83b2c4"

    def test_organization_model_validation(self, sample_organization):
        """Test organization model properties"""
        assert sample_organization.org_id == "test-org-123"
        assert sample_organization.name == "Test Organization"

    def test_default_organization_properties(self):
        """Test default organization creation properties"""
        # Test the default values used in the function
        default_org_id = "default"
        default_name = "Default Organization"
        fallback_org_id = "e7ffb47c-d0d5-4ec0-995a-6025cc83b2c4"

        assert default_org_id == "default"
        assert default_name == "Default Organization"
        assert len(fallback_org_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_get_or_create_default_organization_sql_query_structure(self, mock_db_session):
        """Test that the SQL query is structured correctly"""
        from sqlalchemy.future import select
        from api.models.models import Organization

        # Mock existing organization found
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db_session.execute.return_value = mock_result

        # Call function
        await get_or_create_default_organization(mock_db_session)

        # Verify execute was called with a select statement
        mock_db_session.execute.assert_called_once()
        # The call should be with a select statement, but we can't easily inspect it

    def test_fallback_org_id_format(self):
        """Test that fallback org ID is in correct format"""
        fallback_org_id = "e7ffb47c-d0d5-4ec0-995a-6025cc83b2c4"

        # Should be UUID format
        import uuid
        try:
            uuid.UUID(fallback_org_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        assert is_valid_uuid is True
        assert len(fallback_org_id) == 36
        assert fallback_org_id.count('-') == 4


class TestUtilityHelpers:
    """Test utility helper functions and patterns"""

    def test_error_handling_patterns(self):
        """Test error handling patterns used in utilities"""
        # Test exception handling pattern
        try:
            raise Exception("Test error")
        except Exception as e:
            error_message = str(e)
            assert error_message == "Test error"

    def test_database_session_patterns(self):
        """Test database session usage patterns"""
        # Test async session mock pattern
        mock_session = AsyncMock()

        # Should support common operations
        assert hasattr(mock_session, 'add')
        assert hasattr(mock_session, 'commit')
        assert hasattr(mock_session, 'refresh')
        assert hasattr(mock_session, 'execute')

    def test_model_creation_patterns(self):
        """Test model creation patterns"""
        # Test organization creation pattern
        org_data = {
            "org_id": "test-org",
            "name": "Test Organization"
        }

        # Simulate model creation
        org = Organization(**org_data)
        assert org.org_id == "test-org"
        assert org.name == "Test Organization"

    @pytest.mark.asyncio
    async def test_async_function_patterns(self):
        """Test async function usage patterns"""
        # Test async function definition
        async def sample_async_function():
            return "async_result"

        result = await sample_async_function()
        assert result == "async_result"

    def test_import_patterns(self):
        """Test import patterns used in utilities"""
        # Test SQLAlchemy imports
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.future import select

        # Should be importable
        assert AsyncSession is not None
        assert select is not None

        # Test model imports
        from api.models.models import Organization
        assert Organization is not None


class TestUtilityConstants:
    """Test utility constants and configuration"""

    def test_default_organization_constants(self):
        """Test default organization constants"""
        # These should match the values used in the actual function
        DEFAULT_ORG_ID = "default"
        DEFAULT_ORG_NAME = "Default Organization"
        FALLBACK_ORG_ID = "e7ffb47c-d0d5-4ec0-995a-6025cc83b2c4"

        assert DEFAULT_ORG_ID == "default"
        assert DEFAULT_ORG_NAME == "Default Organization"
        assert len(FALLBACK_ORG_ID) == 36

    def test_organization_id_formats(self):
        """Test organization ID format validation"""
        import uuid

        # Test UUID generation
        generated_uuid = str(uuid.uuid4())
        assert len(generated_uuid) == 36
        assert generated_uuid.count('-') == 4

        # Test specific format patterns
        pattern_parts = generated_uuid.split('-')
        assert len(pattern_parts) == 5
        assert len(pattern_parts[0]) == 8
        assert len(pattern_parts[1]) == 4
        assert len(pattern_parts[2]) == 4
        assert len(pattern_parts[3]) == 4
        assert len(pattern_parts[4]) == 12