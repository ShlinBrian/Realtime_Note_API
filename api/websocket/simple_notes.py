from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import json
import base64
import os
from api.models.models import Note

# Create synchronous database engine for WebSocket (to avoid greenlet issues)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost/notes")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def simple_websocket_handler(websocket: WebSocket, note_id: str):
    """Simple WebSocket handler using synchronous database operations"""
    # Accept connection
    await websocket.accept()
    
    # Extract API key from query parameters
    query_params = dict(websocket.query_params)
    api_key = query_params.get("api_key")
    
    if not api_key:
        await websocket.close(code=1008, reason="API key required")
        return
    
    try:
        # Get initial note data
        with SessionLocal() as db:
            note = db.query(Note).filter(Note.note_id == note_id, Note.deleted == False).first()
            if not note:
                await websocket.close(code=1404, reason="Note not found")
                return
                
            # Send initial note state
            await websocket.send_json({
                "type": "init",
                "data": {
                    "note_id": note.note_id,
                    "title": note.title,
                    "content_md": note.content_md,
                    "version": note.version,
                }
            })
        
        # Message loop
        while True:
            try:
                # Receive message
                message = await websocket.receive_json()
                
                if message.get("type") == "patch":
                    # Process patch
                    data = message.get("data", {})
                    version = data.get("version")
                    patch_b64 = data.get("patch")
                    
                    if not patch_b64:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"code": "INVALID_PATCH", "message": "No patch data"}
                        })
                        continue
                    
                    try:
                        # Decode patch
                        patch_content = json.loads(base64.b64decode(patch_b64).decode())
                        
                        # Update database
                        with SessionLocal() as db:
                            note = db.query(Note).filter(Note.note_id == note_id, Note.deleted == False).first()
                            if not note:
                                await websocket.send_json({
                                    "type": "error", 
                                    "data": {"code": "NOTE_NOT_FOUND", "message": "Note not found"}
                                })
                                continue
                            
                            # Check version
                            if version != note.version:
                                await websocket.send_json({
                                    "type": "error",
                                    "data": {
                                        "code": "VERSION_MISMATCH",
                                        "message": "Version mismatch",
                                        "current_version": note.version
                                    }
                                })
                                continue
                            
                            # Apply patch (simple overwrite for now)
                            if "title" in patch_content:
                                note.title = patch_content["title"]
                            if "content_md" in patch_content:
                                note.content_md = patch_content["content_md"]
                            
                            note.version += 1
                            db.commit()
                            
                            # Send success response
                            await websocket.send_json({
                                "type": "update",
                                "data": {
                                    "title": note.title,
                                    "content_md": note.content_md,
                                    "version": note.version,
                                }
                            })
                            
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"code": "PATCH_ERROR", "message": str(e)}
                        })
                        
            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "data": {"code": "INTERNAL_ERROR", "message": str(e)}
                })
                
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"code": "HANDLER_ERROR", "message": str(e)}
            })
        except:
            pass
        await websocket.close(code=1011)