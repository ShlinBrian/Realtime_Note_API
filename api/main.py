from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import asyncio
import os
import logging
from typing import List, Dict, Any

# Import routers
from api.routers import notes, search, admin, api_keys, auth
from api.grpc.service import serve as serve_grpc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Realtime Notes API",
    description="""
A Kubernetes-native service that delivers real-time, multi-user Markdown note editing plus semantic AI search as a turnkey backend component.

## Features

- **Real-time CRDT Collaboration** via WebSocket
- **CRUD & Versioned Notes** with Markdown support  
- **Vector Search (FAISS)** scoped to tenant
- **Multiple API Surfaces**: REST, gRPC, and WebSocket
- **Authentication** with API Keys and OAuth 2.1
- **RBAC** with row-level isolation
- **Rate Limiting & Quotas**
- **Usage Metering & Billing**

## Quick Start

1. **Create an API Key**: `POST /v1/api-keys`
2. **Create a Note**: `POST /v1/notes` 
3. **Search Notes**: `POST /v1/search`
4. **Real-time Editing**: Connect to `WebSocket /ws/notes/{note_id}`

## Authentication

Use one of these methods:

- **API Key**: Include `x-api-key: your_key` header
- **Bearer Token**: Include `Authorization: Bearer your_token` header

## WebSocket API

For real-time collaboration, connect to:
```
WebSocket: /ws/notes/{note_id}
```

Send JSON patches for collaborative editing with automatic conflict resolution.

## Rate Limits

- **REST API**: 1000 requests/minute per organization
- **WebSocket**: 100 messages/minute per connection
- **Search**: 100 queries/minute per organization

See the `/docs` endpoint for complete API documentation.
""",
    version="1.0.0",
    contact={
        "name": "Realtime Notes API Support",
        "url": "https://github.com/ShlinBrian/Realtime_Note_API",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.example.com", "description": "Production server"},
    ],
    tags_metadata=[
        {
            "name": "notes",
            "description": "CRUD operations for Markdown notes with versioning and search indexing.",
        },
        {
            "name": "search",
            "description": "Semantic vector search across notes using FAISS for high-performance similarity matching.",
        },
        {
            "name": "api-keys",
            "description": "Manage API keys for authentication. Keys are shown only once upon creation.",
        },
        {
            "name": "auth",
            "description": "Authentication endpoints including OAuth 2.1 Device Code flow and token management.",
        },
        {
            "name": "admin",
            "description": "Administrative operations including usage statistics, user management, and billing information.",
        },
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(notes.router)
app.include_router(search.router)
app.include_router(admin.router)
app.include_router(api_keys.router)
app.include_router(auth.router)


# Add WebSocket endpoint
@app.websocket("/ws/notes/{note_id}")
async def websocket_endpoint(websocket: WebSocket, note_id: str):
    from api.websocket.simple_notes import simple_websocket_handler

    await simple_websocket_handler(websocket, note_id)


# Custom exception handler for HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Convert HTTPException to standard error format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": str(exc.status_code), "message": exc.detail}},
    )


# Health check endpoints
@app.get("/health/live", include_in_schema=False)
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
async def readiness_check():
    """Kubernetes readiness probe endpoint"""
    # Here we could check database connection, etc.
    return {"status": "ok"}


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # No security schemes needed anymore
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Start gRPC server when running in production
@app.on_event("startup")
async def startup_event():
    """Start the gRPC server when the app starts"""
    if os.getenv("ENABLE_GRPC", "true").lower() == "true":
        asyncio.create_task(
            serve_grpc(
                host=os.getenv("GRPC_HOST", "0.0.0.0"),
                port=int(os.getenv("GRPC_PORT", "50051")),
            )
        )


# Run the app
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT", "development") == "development",
    )
