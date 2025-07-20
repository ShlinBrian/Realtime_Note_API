from fastapi import WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import json
import base64
import redis
import os
from typing import Dict, List, Any, Optional
import asyncio
import time
import jsonmerge

from api.db.database import SessionLocal
from api.models.models import Note
from api.models.schemas import WebSocketPatch

# Redis connection for pub/sub
REDIS_URL = os.getenv("REDIS_URL", "redis://:redis@localhost:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class NoteConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.connection_details: Dict[WebSocket, Dict[str, Any]] = {}
        self.merger = jsonmerge.Merger(
            # Schema for the merge operation
            {
                "properties": {
                    "content_md": {"mergeStrategy": "overwrite"},
                    "title": {"mergeStrategy": "overwrite"},
                }
            }
        )

    async def connect(self, websocket: WebSocket, note_id: str) -> None:
        """Connect a WebSocket client to a note"""
        await websocket.accept()

        if note_id not in self.active_connections:
            self.active_connections[note_id] = []

        self.active_connections[note_id].append(websocket)
        self.connection_details[websocket] = {
            "note_id": note_id,
            "connected_at": time.time(),
            "bytes_sent": 0,
            "bytes_received": 0,
        }

        # Subscribe to Redis channel for this note
        asyncio.create_task(self._subscribe_to_note(websocket, note_id))

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

    async def _subscribe_to_note(self, websocket: WebSocket, note_id: str) -> None:
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
        """Send a message to a WebSocket client"""
        if websocket not in self.connection_details:
            return

        details = self.connection_details[websocket]

        # Convert message to string and calculate bytes
        message_str = json.dumps(message)
        bytes_count = len(message_str.encode("utf-8"))

        # Update bytes count
        details["bytes_sent"] += bytes_count

        # Send message
        await websocket.send_json(message)

    def apply_patch(
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


def get_note_if_exists_sync(note_id: str, db) -> Note:
    """Get a note if it exists (synchronous version for WebSocket)"""
    note = db.query(Note).filter(Note.note_id == note_id, Note.deleted == False).first()

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found",
        )

    return note


async def get_note_if_exists(note_id: str, db: AsyncSession) -> Note:
    """Get a note if it exists"""
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
):
    """Handle WebSocket connection for real-time note editing"""
    print(f"DEBUG: Starting WebSocket handler for note {note_id}")
    try:
        # Accept the WebSocket connection first
        print("DEBUG: Accepting WebSocket connection")
        await websocket.accept()
        print("DEBUG: WebSocket accepted")

        # Extract API key from query parameters
        query_params = dict(websocket.query_params)
        api_key = query_params.get("api_key")
        print(f"DEBUG: API key: {api_key}")

        # Simple API key check - accept any non-empty key for now
        if not api_key:
            print("DEBUG: No API key, closing connection")
            await websocket.close(code=1008, reason="API key required")
            return

        # Use synchronous database operations to avoid greenlet issues
        # Get the note initially and send init message
        print("DEBUG: Creating database session")
        with SessionLocal() as db:
            print("DEBUG: Getting note from database")
            note = get_note_if_exists_sync(note_id, db)

            # Add to connection manager (but don't call accept again)
            if note_id not in manager.active_connections:
                manager.active_connections[note_id] = []
            manager.active_connections[note_id].append(websocket)
            manager.connection_details[websocket] = {
                "note_id": note_id,
                "connected_at": time.time(),
                "bytes_sent": 0,
                "bytes_received": 0,
            }

            # Send initial note state
            await websocket.send_json(
                {
                    "type": "init",
                    "data": {
                        "note_id": note.note_id,
                        "title": note.title,
                        "content_md": note.content_md,
                        "version": note.version,
                    },
                }
            )

        # Handle incoming messages - each operation gets its own DB session
        print("DEBUG: Starting message loop")
        while True:
            try:
                print("DEBUG: Waiting for message...")
                # Receive JSON message
                message = await websocket.receive_json()
                print(f"DEBUG: Received message: {message}")

                # Handle patch
                if message.get("type") == "patch":
                    try:
                        print("DEBUG: Creating patch data")
                        patch_data = WebSocketPatch(**message.get("data", {}))
                        print(f"DEBUG: Patch data created: {patch_data}")

                        # Create fresh synchronous database session for this operation
                        print("DEBUG: Opening database session")
                        with SessionLocal() as db:
                            # Get current note state
                            note = get_note_if_exists_sync(note_id, db)

                            # Check version
                            if patch_data.version != note.version:
                                await websocket.send_json(
                                    {
                                        "type": "error",
                                        "data": {
                                            "code": "VERSION_MISMATCH",
                                            "message": "Note version mismatch",
                                            "current_version": note.version,
                                        },
                                    }
                                )
                                continue

                            # Apply patch
                            note_content = {
                                "title": note.title,
                                "content_md": note.content_md,
                            }
                            updated_content = manager.apply_patch(
                                note_content, patch_data.patch
                            )

                            # Update note in database
                            note.title = updated_content.get("title", note.title)
                            note.content_md = updated_content.get(
                                "content_md", note.content_md
                            )
                            note.version += 1

                            db.add(note)
                            db.commit()  # Synchronous commit

                            # Prepare update message
                            update_message = {
                                "type": "update",
                                "data": {
                                    "title": note.title,
                                    "content_md": note.content_md,
                                    "version": note.version,
                                },
                            }

                        # Send to all connected clients for this note (outside db session)
                        if note_id in manager.active_connections:
                            for client_ws in manager.active_connections[note_id]:
                                if client_ws != websocket:  # Don't send to sender
                                    try:
                                        await client_ws.send_json(update_message)
                                    except:
                                        pass  # Client might be disconnected
                    except Exception as e:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "data": {"code": "PATCH_ERROR", "message": str(e)},
                            }
                        )
            except WebSocketDisconnect:
                break
            except Exception as e:
                # Send error to client
                print(f"WebSocket error in message handling: {e}")
                print(f"Error type: {type(e)}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "data": {
                            "code": "INTERNAL_ERROR",
                            "message": str(e),
                        },
                    }
                )
    except HTTPException as e:
        # Send error and close
        if websocket.client_state.name == "CONNECTED":
            await websocket.send_json(
                {
                    "type": "error",
                    "data": {
                        "code": str(e.status_code),
                        "message": e.detail,
                    },
                }
            )
            await websocket.close(code=e.status_code)
    except Exception as e:
        # Handle unexpected errors
        if websocket.client_state.name == "CONNECTED":
            await websocket.close(code=1011, reason="Internal server error")
    finally:
        # Disconnect WebSocket
        await manager.disconnect(websocket)
