# Test Suite

This directory contains comprehensive tests for the Realtime Notes API, organized to achieve 80%+ code coverage through both unit and integration testing.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (isolated, fast)
│   ├── test_models.py       # Database model tests
│   ├── test_schemas.py      # Pydantic schema validation tests
│   ├── test_vector_search.py # Vector search functionality tests
│   └── test_auth.py         # Authentication and rate limiting tests
├── integration/             # Integration tests (end-to-end)
│   ├── test_notes_api.py    # Notes CRUD API tests
│   ├── test_search_api.py   # Search API tests
│   └── test_websocket.py    # WebSocket collaboration tests
└── fixtures/                # Test data and utilities
```

## Test Categories

### Unit Tests
- **Models**: Database model validation, relationships, constraints
- **Schemas**: Pydantic schema validation and edge cases
- **Vector Search**: Embedding generation, FAISS indexing, similarity search
- **Authentication**: API key validation, rate limiting, security

### Integration Tests
- **Notes API**: Complete CRUD operations with database
- **Search API**: End-to-end search functionality
- **WebSocket**: Real-time collaboration and message handling

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Or use the test runner
python run_tests.py install
```

### Basic Usage

```bash
# Run all tests with coverage
pytest

# Run specific test categories
pytest tests/unit/           # Unit tests only
pytest tests/integration/    # Integration tests only

# Run with coverage report
pytest --cov=api --cov-report=html

# Run specific test patterns
pytest -k "test_search"      # All search-related tests
pytest -k "test_models"      # All model tests
```

### Using Test Runner

```bash
# Run all tests (default)
python run_tests.py

# Run specific test types
python run_tests.py unit           # Unit tests only
python run_tests.py integration    # Integration tests only
python run_tests.py fast           # Quick tests (no coverage)

# Run tests matching pattern
python run_tests.py -k "search"    # Search-related tests

# Install dependencies and run tests
python run_tests.py --install-deps
```

## Test Configuration

### Coverage Requirements
- Minimum 80% code coverage required
- HTML coverage reports generated in `htmlcov/`
- Terminal coverage report shows missing lines

### Test Database
- Uses SQLite in-memory database for speed
- Fresh database created for each test
- Automatic cleanup after tests

### Mocking
- External services (Redis, FAISS) are mocked by default
- Vector search can run with or without actual FAISS
- WebSocket tests may skip if server unavailable

## Test Fixtures

### Database Fixtures
- `test_session`: Synchronous database session
- `async_test_session`: Asynchronous database session
- `test_org`: Test organization
- `test_user`: Test user
- `test_note`: Test note
- `test_api_key`: Test API key

### Authentication Fixtures
- `auth_headers`: Valid API key headers
- `mock_auth_user`: Mocked authenticated user

### Vector Search Fixtures
- `mock_vector_search`: Mocked vector search operations
- `temp_index_dir`: Temporary directory for indices

### Utility Fixtures
- `mock_redis`: Mocked Redis client
- `sample_notes_data`: Sample note data for testing

## Writing New Tests

### Unit Test Example

```python
def test_create_note(test_session, test_org):
    """Test creating a note"""
    note = Note(
        note_id=str(uuid.uuid4()),
        org_id=test_org.org_id,
        title="Test Note",
        content_md="Test content",
        version=1
    )
    test_session.add(note)
    test_session.commit()

    assert note.note_id is not None
    assert note.title == "Test Note"
```

### Integration Test Example

```python
def test_create_note_api(test_client, auth_headers):
    """Test note creation via API"""
    note_data = {
        "title": "Test Note",
        "content_md": "Test content"
    }

    response = test_client.post("/v1/notes", json=note_data, headers=auth_headers)

    assert response.status_code == 201
    note_id = response.json()
    assert isinstance(note_id, str)
```

## Test Best Practices

### Naming Conventions
- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

### Test Organization
- Group related tests in classes
- Use descriptive test names
- Test both success and failure cases
- Include edge cases and boundary conditions

### Assertions
- Use specific assertions (`assert x == y` not `assert x`)
- Test one concept per test function
- Include error message context when helpful

### Test Data
- Use fixtures for reusable test data
- Create minimal test data needed
- Clean up after tests (handled automatically)

## Coverage Goals

### Unit Tests (Target: 90%+)
- ✅ Models and database operations
- ✅ Schema validation and serialization
- ✅ Vector search algorithms
- ✅ Authentication and authorization
- ✅ Rate limiting logic

### Integration Tests (Target: 80%+)
- ✅ API endpoint functionality
- ✅ Database integration
- ✅ WebSocket communication
- ✅ Search functionality
- ✅ Error handling

### Overall Coverage Target: 80%+

## Continuous Integration

Tests are designed to run in CI environments:
- No external dependencies required
- Fast execution (< 2 minutes)
- Clear pass/fail indicators
- Coverage reporting
- Parallel execution support

## Debugging Tests

### Verbose Output
```bash
pytest -v                    # Verbose test names
pytest -s                    # Don't capture output
pytest --tb=long            # Full tracebacks
```

### Running Single Tests
```bash
pytest tests/unit/test_models.py::TestNote::test_create_note
pytest -k "test_create_note"
```

### Coverage Analysis
```bash
pytest --cov=api --cov-report=html
# Open htmlcov/index.html to see detailed coverage
```

## Test Maintenance

### Adding New Features
1. Write tests first (TDD approach)
2. Ensure new code has 80%+ coverage
3. Update fixtures if needed
4. Add integration tests for API changes

### Updating Tests
1. Keep tests in sync with code changes
2. Update mocks when external APIs change
3. Refresh test data as needed
4. Maintain documentation

### Performance
- Unit tests should be fast (< 100ms each)
- Integration tests should be reasonable (< 5s each)
- Use mocking to avoid slow operations
- Parallelize when possible