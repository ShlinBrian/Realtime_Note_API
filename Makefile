.PHONY: api-run api-dev db-run docker-up docker-down docker-logs install test clean help generate-grpc

# Default target
help:
	@echo "Available commands:"
	@echo "  make api-run       - Run the API server"
	@echo "  make api-dev       - Run the API server in development mode with auto-reload"
	@echo "  make db-run        - Run PostgreSQL and Redis with Docker"
	@echo "  make docker-up     - Start all services with Docker Compose"
	@echo "  make docker-down   - Stop all Docker Compose services"
	@echo "  make docker-logs   - Show logs from Docker Compose services"
	@echo "  make install       - Install dependencies"
	@echo "  make test          - Run tests"
	@echo "  make clean         - Clean up temporary files and volumes"
	@echo "  make generate-grpc - Generate gRPC code from proto files"

# Run API server
api-run: generate-grpc
	uvicorn api.main:app --host 0.0.0.0 --port 8000

# Run API server in development mode with auto-reload
api-dev: generate-grpc
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Run PostgreSQL and Redis with Docker
db-run:
	docker-compose up -d postgres redis pgadmin

# Docker Compose commands
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "Install development dependencies? [y/N] " && read ans && [ $${ans:-N} = y ] && pip install -r requirements-dev.txt || true

# Generate gRPC code
generate-grpc:
	@echo "Generating gRPC code..."
	bash scripts/generate_grpc.sh

# Run tests
test:
	pytest

# Clean up
clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +/
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +/
	find . -type d -name "*.egg" -exec rm -rf {} +/
	find . -type d -name ".pytest_cache" -exec rm -rf {} +/
	find . -type d -name ".coverage" -exec rm -rf {} +/
	find . -type d -name "htmlcov" -exec rm -rf {} +/
	find . -type d -name ".mypy_cache" -exec rm -rf {} +/
	rm -f local_api_key.txt
