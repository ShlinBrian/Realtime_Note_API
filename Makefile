.PHONY: run dev test clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  make run   - Start all services with Docker (recommended)"
	@echo "  make dev   - Run API locally for development (requires conda)"
	@echo "  make test  - Run tests"
	@echo "  make clean - Stop services and clean everything"

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

# Run tests
test:
	@bash -c "source $$(conda info --base)/etc/profile.d/conda.sh && conda activate realtime-note-api && pytest"

# Stop services and clean everything
clean:
	@echo "Stopping all services..."
	@docker compose down -v
	@echo "Cleaning temporary files..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -f local_api_key.txt
	@echo "Cleanup complete."
