#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test_websocket():
    note_id = "c7a3004a-1817-43d1-8d2a-33a15961f86b"
    api_key = "test123"
    
    uri = f"ws://localhost:8000/ws/notes/{note_id}?api_key={api_key}"
    
    try:
        print(f"Connecting to: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected!")
            
            # Wait for initial message
            initial_message = await websocket.recv()
            print(f"Received: {initial_message}")
            
            # Send a patch message
            patch_content = {
                "title": "Test Title", 
                "content_md": "# Test Content\n\nThis is a test from Python WebSocket client."
            }
            
            import base64
            patch_data = base64.b64encode(json.dumps(patch_content).encode()).decode()
            
            patch_message = {
                "type": "patch",
                "data": {
                    "version": 4,  # Current version from the notes list
                    "patch": patch_data
                }
            }
            
            print(f"Sending patch: {patch_message}")
            await websocket.send(json.dumps(patch_message))
            
            # Wait for response
            response = await websocket.recv()
            print(f"Response: {response}")
            
    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_websocket())