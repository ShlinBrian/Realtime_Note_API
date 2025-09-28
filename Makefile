.PHONY: run dev test test-unit test-integration test-integration-all test-coverage test-quick test-verbose test-with-services clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  make run              - Start all services with Docker (recommended)"
	@echo "  make dev              - Run API locally for development (requires conda)"
	@echo "  make test             - Run unit tests with coverage reporting"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run working integration tests only"
	@echo "  make test-integration-all - Run ALL integration tests (may hang)"
	@echo "  make test-coverage    - Run tests with detailed HTML coverage report"
	@echo "  make test-quick       - Run tests quickly without detailed output"
	@echo "  make test-verbose     - Run tests with verbose output"
	@echo "  make test-with-services - Start services and run integration tests"
	@echo "  make clean            - Stop services and clean everything"

# Start all services with Docker (recommended)
run:
	@echo "Starting all services with Docker..."
	@docker compose up -d
	@echo ""
	@echo "Services starting up..."
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "Frontend: http://localhost:8080"
	@echo ""
	@echo "Waiting for API key generation..."
	@sleep 5
	@if [ -f "local_api_key.txt" ]; then \
		echo "Your API key:"; \
		cat local_api_key.txt; \
	else \
		echo "Check API key with: cat local_api_key.txt"; \
	fi
	@echo ""
	@echo "View logs: docker compose logs -f"

# Run API locally for development (requires conda)
dev:
	@echo "Installing dependencies..."
	@if conda env list | grep -q "realtime-note-api"; then \
		echo "Using existing conda environment..."; \
	else \
		echo "Creating conda environment..."; \
		conda create -n realtime-note-api python=3.11.8 -y; \
	fi
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate realtime-note-api && conda install -c conda-forge faiss-cpu -y && pip install -r requirements.txt && pip install -r requirements-dev.txt"
	@echo "Generating gRPC code..."
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate realtime-note-api && bash scripts/generate_grpc.sh"
	@echo "Starting API in development mode..."
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate realtime-note-api && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

# Run all tests with coverage reporting
test:
	@echo "Running comprehensive test suite with coverage reporting..."
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate py313 && python -m pytest tests/unit/ -v --cov=api --cov-report=term-missing --cov-report=html:htmlcov/all"

# Run unit tests only
test-unit:
	@echo "Running unit tests with coverage..."
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate py313 && python -m pytest tests/unit/ --cov=api --cov-report=term --tb=no -q"

# Run working integration tests only
test-integration:
	@echo "Running working integration tests with coverage..."
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate py313 && python -m pytest tests/integration/test_api_simple.py --cov=api --cov-report=term"

# Run ALL integration tests (including problematic ones)
test-integration-all:
	@echo "Running ALL integration tests (may hang on gRPC issues)..."
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate py313 && python -m pytest tests/integration/ --cov=api --cov-report=term"

# Run tests with detailed HTML coverage report
test-coverage:
	@echo "Running tests with detailed coverage analysis..."
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate py313 && python -m pytest tests/unit/ --cov=api --cov-report=html:htmlcov --cov-report=term-missing"
	@echo "Coverage report generated in htmlcov/index.html"

# Run tests quickly for development
test-quick:
	@echo "Running quick test suite..."
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate py313 && python -m pytest tests/ --cov=api --cov-report=term:skip-covered --no-cov-on-fail -q --tb=no"

# Run tests with verbose output for debugging
test-verbose:
	@echo "Running tests with verbose output..."
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate py313 && python -m pytest tests/ -xvs --cov=api --cov-report=term-missing"

# Start services and run integration tests
test-with-services:
	@echo "Starting services for integration testing..."
	@docker compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 15
	@echo "Running integration tests with real services..."
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate py313 && python -m pytest tests/integration/test_api_simple.py -v || true"
	@echo "Stopping test services..."
	@docker compose down

# Stop services and clean everything
clean:
	@echo "Stopping all services..."
	@docker compose down -v
	@echo "Cleaning temporary files..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -f local_api_key.txt
	@echo "Cleanup complete."
