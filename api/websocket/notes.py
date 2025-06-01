from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import json
import base64
import redis
import os
from typing import Dict, List, Set, Any, Optional
import asyncio
import time
import jsonmerge

from api.db.database import get_async_db, set_tenant_context
from api.models.models import Note, User
from api.models.schemas import WebSocketPatch
from api.auth.auth import get_current_user_from_token, get_current_user_from_api_key
from api.auth.rate_limit import RateLimiter, DEFAULT_BYTES_PER_MINUTE
from api.billing.usage import log_usage

# Redis connection for pub/sub
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class NoteConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.connection_details: Dict[WebSocket, Dict[str, Any]] = {}
        self.rate_limiter = RateLimiter()
        self.merger = jsonmerge.Merger(
            # Schema for the merge operation
            {
                "properties": {
                    "content_md": {"mergeStrategy": "overwrite"},
                    "title": {"mergeStrategy": "overwrite"},
                }
            }
        )

    async def connect(
        self, websocket: WebSocket, note_id: str, user: User, org_id: str
    ) -> None:
        """Connect a WebSocket client to a note"""
        await websocket.accept()

        if note_id not in self.active_connections:
            self.active_connections[note_id] = []

        self.active_connections[note_id].append(websocket)
        self.connection_details[websocket] = {
            "note_id": note_id,
            "user_id": user.user_id if user else None,
            "org_id": org_id,
            "connected_at": time.time(),
            "bytes_sent": 0,
            "bytes_received": 0,
        }

        # Subscribe to Redis channel for this note
        asyncio.create_task(self._subscribe_to_note(websocket, note_id, org_id))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Disconnect a WebSocket client"""
        if websocket not in self.connection_details:
            return

        details = self.connection_details[websocket]
        note_id = details["note_id"]

        if note_id in self.active_connections:
            if websocket in self.active_connections[note_id]:
                self.active_connections[note_id].remove(websocket)

            if not self.active_connections[note_id]:
                del self.active_connections[note_id]

        if websocket in self.connection_details:
            del self.connection_details[websocket]

    async def broadcast_to_note(
        self, note_id: str, message: Dict[str, Any], exclude: Optional[WebSocket] = None
    ) -> None:
        """Broadcast a message to all clients connected to a note"""
        # Publish to Redis channel
        redis_client.publish(f"note:{note_id}", json.dumps(message))

    async def _subscribe_to_note(
        self, websocket: WebSocket, note_id: str, org_id: str
    ) -> None:
        """Subscribe to Redis channel for a note"""
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"note:{note_id}")

        try:
            for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                if websocket not in self.connection_details:
                    break

                data = json.loads(message["data"])
                await self._send_message(websocket, data)
        except Exception:
            pass
        finally:
            pubsub.unsubscribe(f"note:{note_id}")

    async def _send_message(
        self, websocket: WebSocket, message: Dict[str, Any]
    ) -> None:
        """Send a message to a WebSocket client with rate limiting"""
        if websocket not in self.connection_details:
            return

        details = self.connection_details[websocket]
        org_id = details["org_id"]

        # Convert message to string and calculate bytes
        message_str = json.dumps(message)
        bytes_count = len(message_str.encode("utf-8"))

        # Check rate limit
        allowed = await self.rate_limiter.check_rate_limit(
            org_id=org_id, kind="WS", bytes_count=bytes_count
        )

        if not allowed:
            await websocket.close(code=4008, reason="Rate limit exceeded")
            return

        # Update bytes count
        details["bytes_sent"] += bytes_count

        # Send message
        await websocket.send_json(message)

    async def apply_patch(
        self, note_content: Dict[str, Any], patch_data: str
    ) -> Dict[str, Any]:
        """Apply a JSON patch to note content using jsonmerge"""
        try:
            # Decode the base64 patch data
            patch_json = json.loads(base64.b64decode(patch_data).decode("utf-8"))

            # Use jsonmerge to merge the patch with the original content
            merged_content = self.merger.merge(note_content, patch_json)
            return merged_content
        except Exception as e:
            # Log the error and return the original content
            print(f"Error applying patch: {e}")
            return note_content


# Global connection manager
manager = NoteConnectionManager()


async def get_note_if_exists(note_id: str, db: AsyncSession, org_id: str) -> Note:
    """Get a note if it exists and belongs to the organization"""
    # Set tenant context for RLS
    await set_tenant_context(db, org_id)

    result = await db.execute(
        select(Note).where(Note.note_id == note_id, Note.deleted == False)
    )
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    return note


async def handle_websocket_connection(
    websocket: WebSocket,
    note_id: str,
    token: Optional[str] = None,
    api_key: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Handle WebSocket connection for real-time note editing"""
    user = None
    org_id = None

    # Authenticate user
    try:
        if token:
            user, org_id = await get_current_user_from_token(token, db)
        elif api_key:
            user, org_id = await get_current_user_from_api_key(api_key, db)
        else:
            await websocket.close(code=1008, reason="Authentication required")
            return
    except HTTPException:
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Check if note exists
    try:
        note = await get_note_if_exists(note_id, db, org_id)
    except HTTPException as e:
        await websocket.close(code=1008, reason=str(e.detail))
        return

    # Connect to WebSocket
    await manager.connect(websocket, note_id, user, org_id)

    try:
        # Process messages
        while True:
            # Receive message
            data = await websocket.receive_text()

            # Parse message
            try:
                message_data = json.loads(data)
                patch = WebSocketPatch(**message_data)
            except (json.JSONDecodeError, ValueError):
                await websocket.send_json({"error": "Invalid message format"})
                continue

            # Calculate bytes
            bytes_count = len(data.encode("utf-8"))

            # Check rate limit
            allowed = await manager.rate_limiter.check_rate_limit(
                org_id=org_id, kind="WS", bytes_count=bytes_count
            )

            if not allowed:
                await websocket.close(code=4008, reason="Rate limit exceeded")
                return

            # Get current note content
            note_content = {"title": note.title, "content_md": note.content_md}

            # Apply patch to note content
            updated_content = await manager.apply_patch(note_content, patch.patch)

            # Update note in database
            note.title = updated_content.get("title", note.title)
            note.content_md = updated_content.get("content_md", note.content_md)
            note.version = patch.version
            db.add(note)
            await db.commit()

            # Broadcast to other clients
            await manager.broadcast_to_note(
                note_id=note_id,
                message={"patch": patch.patch, "version": patch.version},
                exclude=websocket,
            )

            # Log usage
            connection_details = manager.connection_details.get(websocket, {})
            connection_details["bytes_received"] = (
                connection_details.get("bytes_received", 0) + bytes_count
            )

            await log_usage(
                org_id=org_id,
                user_id=user.user_id if user else None,
                kind="WS",
                endpoint=f"/ws/notes/{note_id}",
                bytes_count=bytes_count,
                db=db,
            )

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
