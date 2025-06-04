# Realtime Notes API

A Kubernetes-native service that delivers real-time, multi-user Markdown note editing plus semantic AI search as a turnkey backend component.

## Features

- Real-time CRDT collaboration via WebSocket
- CRUD & versioned fetch of Markdown notes
- Vector search (FAISS) scoped to tenant
- Multiple API surfaces: REST, gRPC, and WebSocket
- Authentication with API Keys and OAuth 2.1
- RBAC with row-level isolation
- Rate limiting & quotas
- Usage metering & billing

## Quick Start

### Prerequisites

- Kubernetes 1.28+ cluster (kind, minikube, or any managed K8s)
- Helm v3
- kubectl

### Installation

```bash
# Clone the repository
git clone https://github.com/ShlinBrian/Realtime_Note_API
cd realtime-note-api

# Install with Helm
helm install realtime-notes ./helm/realtime-notes
```

### Using the API

```bash
# Get API key
export API_KEY=$(kubectl get secret realtime-note-api-keys -o jsonpath='{.data.admin-key}' | base64 -d)

# Create a note
curl -X POST "https://your-cluster-ip/v1/notes" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "My First Note", "content_md": "# Hello World\n\nThis is a test note."}'
```

## Local Development with Docker Compose

The easiest way to run the application locally is using Docker Compose:

```bash
# Using Make
make docker-up

# Or using Docker Compose directly
docker compose up -d
```

Once the services are running:

1. Access the API at http://localhost:8000
2. API documentation is available at http://localhost:8000/docs
3. The initial API key is generated and saved in `local_api_key.txt`
4. PgAdmin is available at http://localhost:5050 (login: admin@example.com / admin)

### Testing the API Locally

```bash
# Get the API key
API_KEY=$(cat local_api_key.txt | grep -oP 'API_KEY=\K.*')

# Create a note
curl -X POST "http://localhost:8000/v1/notes" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "My First Note", "content_md": "# Hello World\n\nThis is a test note."}'
```

## Development

You have two options for setting up your development environment:

### Option 1: Using conda (recommended for FAISS support)

```bash
# Create and activate conda environment
conda create --name realtime-note-api python=3.11
conda activate realtime-note-api

# Install FAISS via conda
conda install -c conda-forge faiss-cpu

# Install dependencies
make install

# Generate gRPC code (required before running the API)
make generate-grpc

# Run the API in development mode
make api-dev
```

### Option 2: Using pip with venv

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
make install

# Generate gRPC code (required before running the API)
make generate-grpc

# Run tests
make test

# Run the API in development mode
make api-dev
```

### Using Make

The project includes a Makefile with useful commands for development:

```bash
# Show all available commands
make help

# Run the API server
make api-run

# Run the API server in development mode with auto-reload
make api-dev

# Run only the database services
make db-run

# Start all Docker services
make docker-up

# View Docker logs
make docker-logs

# Stop Docker services
make docker-down

# Install dependencies
make install

# Generate gRPC code from proto files
make generate-grpc

# Run tests
make test

# Clean up temporary files and volumes
make clean
```

### Helper Script

The `run_local.sh` script provides several useful commands:

```bash
# Install dependencies
./run_local.sh install

# Start Docker services
./run_local.sh start

# View logs
./run_local.sh logs

# Get API key
./run_local.sh key

# Stop services
./run_local.sh stop

# Clean up everything
./run_local.sh clean
```

## Documentation

API documentation is available at `/docs` when the service is running.

## License

MIT
