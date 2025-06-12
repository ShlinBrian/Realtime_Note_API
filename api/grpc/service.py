import grpc
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict, AsyncGenerator, List, Tuple, Any
import base64
import json
import jsonmerge

# Import generated gRPC code
from api.grpc.generated import notes_pb2, notes_pb2_grpc

# Import models and services
from api.db.database import get_async_db
from api.models.models import Note, User, ApiKey, UserRole
from api.search.vector_search import search_notes
from api.auth.auth import hash_api_key


class NoteServiceServicer(notes_pb2_grpc.NoteServiceServicer):
    """Implementation of the NoteService gRPC service"""

    def __init__(self, db_getter):
        self.db_getter = db_getter
        self.edit_connections: Dict[str, List[grpc.aio.StreamStreamCall]] = {}
        self.merger = jsonmerge.Merger(
            # Schema for the merge operation
            {
                "properties": {
                    "content_md": {"mergeStrategy": "overwrite"},
                    "title": {"mergeStrategy": "overwrite"},
                }
            }
        )

    async def authenticate(self, context) -> Tuple[User, str]:
        """Authenticate the gRPC request using metadata"""
        metadata = dict(context.invocation_metadata())

        # Check for API key
        api_key = metadata.get("x-api-key")
        if api_key:
            db = next(self.db_getter())

            # Find API key
            result = await db.execute(
                select(ApiKey).where(ApiKey.hash == hash_api_key(api_key))
            )
            db_api_key = result.scalar_one_or_none()

            if not db_api_key:
                await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid API key")

            # Check if expired
            if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED, "API key has expired"
                )

            # Get organization owner as user
            result = await db.execute(
                select(User)
                .where(User.org_id == db_api_key.org_id)
                .where(User.role == UserRole.OWNER)
                .limit(1)
            )
            user = result.scalar_one_or_none()

            if not user:
                await context.abort(
                    grpc.StatusCode.INTERNAL, "Organization has no owner"
                )

            return user, db_api_key.org_id

        # Check for JWT token
        token = metadata.get("authorization", "").replace("Bearer ", "")
        if token:
            # JWT validation would go here
            # For now, return unauthorized
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "JWT not implemented")

        await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Authentication required")

    async def GetNote(self, request, context):
        """Get a note by ID"""
        try:
            # Authenticate
            user, org_id = await self.authenticate(context)

            # Get database session
            db = next(self.db_getter())

            # Get note
            result = await db.execute(
                select(Note).where(
                    Note.note_id == request.note_id, Note.deleted == False
                )
            )
            note = result.scalar_one_or_none()

            if not note:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Note with ID {request.note_id} not found",
                )

            # Convert to gRPC response
            return notes_pb2.Note(
                note_id=note.note_id,
                title=note.title,
                content_md=note.content_md,
                version=note.version,
                created_at=note.created_at.isoformat(),
                updated_at=note.updated_at.isoformat(),
            )

        except Exception as e:
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def Search(self, request, context):
        """Search for notes"""
        try:
            # Authenticate
            user, org_id = await self.authenticate(context)

            # Get database session
            db = next(self.db_getter())

            # Search for notes
            results = await search_notes(
                query=request.query, org_id=org_id, top_k=request.top_k, db=db
            )

            # Convert to gRPC response
            search_results = [
                notes_pb2.SearchResult(note_id=note_id, score=score)
                for note_id, score in results
            ]

            return notes_pb2.SearchResponse(results=search_results)

        except Exception as e:
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def apply_patch(
        self, note_content: Dict[str, Any], patch_data: bytes
    ) -> Dict[str, Any]:
        """Apply a JSON patch to note content using jsonmerge"""
        try:
            # Decode the patch data
            patch_json = json.loads(patch_data.decode("utf-8"))

            # Use jsonmerge to merge the patch with the original content
            merged_content = self.merger.merge(note_content, patch_json)
            return merged_content
        except Exception as e:
            # Log the error and return the original content
            print(f"Error applying patch: {e}")
            return note_content

    async def Edit(self, request_iterator, context):
        """Bidirectional streaming for real-time editing"""
        user = None
        org_id = None
        note_id = None
        db = None

        try:
            # Authenticate
            user, org_id = await self.authenticate(context)

            # Get database session
            db = next(self.db_getter())

            # Process incoming messages
            async for request in request_iterator:
                # First message sets the note ID
                if note_id is None:
                    note_id = request.note_id

                    # Check if note exists
                    result = await db.execute(
                        select(Note).where(
                            Note.note_id == note_id, Note.deleted == False
                        )
                    )
                    note = result.scalar_one_or_none()

                    if not note:
                        await context.abort(
                            grpc.StatusCode.NOT_FOUND,
                            f"Note with ID {note_id} not found",
                        )

                    # Add to connections
                    if note_id not in self.edit_connections:
                        self.edit_connections[note_id] = []

                    self.edit_connections[note_id].append(context)

                # Process patch
                if note_id != request.note_id:
                    await context.abort(
                        grpc.StatusCode.INVALID_ARGUMENT,
                        "Cannot change note ID during session",
                    )

                # Get current note
                result = await db.execute(select(Note).where(Note.note_id == note_id))
                note = result.scalar_one_or_none()

                if note:
                    # Get current note content
                    note_content = {"title": note.title, "content_md": note.content_md}

                    # Apply patch to note content
                    updated_content = await self.apply_patch(
                        note_content, request.patch
                    )

                    # Update note in database
                    note.title = updated_content.get("title", note.title)
                    note.content_md = updated_content.get("content_md", note.content_md)
                    note.version = request.version
                    db.add(note)
                    await db.commit()

                # Broadcast to other connections
                if note_id in self.edit_connections:
                    for conn in self.edit_connections[note_id]:
                        if conn != context:  # Don't send back to sender
                            try:
                                await conn.write(request)
                            except:
                                pass

                # Send back to client as confirmation
                yield request

        except Exception as e:
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

        finally:
            # Clean up connection
            if (
                note_id in self.edit_connections
                and context in self.edit_connections[note_id]
            ):
                self.edit_connections[note_id].remove(context)

                if not self.edit_connections[note_id]:
                    del self.edit_connections[note_id]


async def serve(host="0.0.0.0", port=50051):
    """Start the gRPC server"""
    server = grpc.aio.server()
    notes_pb2_grpc.add_NoteServiceServicer_to_server(
        NoteServiceServicer(get_async_db), server
    )
    server.add_insecure_port(f"{host}:{port}")
    await server.start()

    print(f"gRPC server started on {host}:{port}")

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        await server.stop(0)
        print("gRPC server stopped")
