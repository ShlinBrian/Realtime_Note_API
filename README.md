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
git clone https://github.com/yourusername/realtime-notes-api.git
cd realtime-notes-api

# Install with Helm
helm install realtime-notes ./helm/realtime-notes
```

### Using the API

```bash
# Get API key
export API_KEY=$(kubectl get secret realtime-notes-api-keys -o jsonpath='{.data.admin-key}' | base64 -d)

# Create a note
curl -X POST "https://your-cluster-ip/v1/notes" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "My First Note", "content_md": "# Hello World\n\nThis is a test note."}'
```

## Development

### Using conda (recommended)

```bash
# Create conda environment
conda create --name realtime-notes-api python=3.11
conda activate realtime-notes-api

# Install FAISS via conda
conda install -c conda-forge faiss-cpu

# Install the package in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run local development server
uvicorn api.main:app --reload
```

### Using pip

```bash
# Set up local development environment
python -m venv venv
source venv/bin/activate

# Install the package without FAISS (simple search will be used)
pip install -e .

# Or install with FAISS (may require additional dependencies)
pip install -e ".[faiss]"

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run local development server
uvicorn api.main:app --reload
```

## Documentation

API documentation is available at `/docs` when the service is running.

## License

MIT
