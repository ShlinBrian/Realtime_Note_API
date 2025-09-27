"""
Test suite for Realtime Notes API

This test suite provides comprehensive coverage including:
- Unit tests for models, schemas, and core functionality
- Integration tests for API endpoints
- WebSocket integration tests
- Authentication and rate limiting tests
- Vector search functionality tests

Usage:
    pytest                          # Run all tests
    pytest tests/unit/              # Run unit tests only
    pytest tests/integration/       # Run integration tests only
    pytest --cov=api                # Run with coverage report
    pytest -v                       # Verbose output
    pytest -k "test_search"         # Run tests matching pattern
"""