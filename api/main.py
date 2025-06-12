from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import asyncio
import os
import logging
from typing import List, Dict, Any

# Import routers
from api.routers import notes, search, admin, api_keys, auth
from api.websocket.notes import handle_websocket_connection
from api.grpc.service import serve as serve_grpc
from api.models.schemas import ErrorResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Realtime Notes API",
    description="A Kubernetes-native service that delivers real-time, multi-user Markdown note editing plus semantic AI search as a turnkey backend component.",
    version="1.0.0",
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
app.add_websocket_route("/ws/notes/{note_id}", handle_websocket_connection)


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
