#!/usr/bin/env python3
import asyncio
import websockets
import json
import base64

async def test_websocket_patch():
    note_id = "c7a3004a-1817-43d1-8d2a-33a15961f86b"
    api_key = "test123"
    
    uri = f"ws://localhost:8000/ws/notes/{note_id}?api_key={api_key}"
    
    try:
        print(f"Connecting to: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected!")
            
            # Wait for initial message
            initial_message = await websocket.recv()
            print(f"✅ Received: {initial_message}")
            
            # Parse initial message to get current version
            init_data = json.loads(initial_message)
            current_version = init_data["data"]["version"]
            print(f"Current version: {current_version}")
            
            # Send a patch message
            patch_content = {
                "title": "Test Title Updated", 
                "content_md": "# Test Content\n\nThis is a test from Python WebSocket client - UPDATED!"
            }
            
            patch_data = base64.b64encode(json.dumps(patch_content).encode()).decode()
            
            patch_message = {
                "type": "patch",
                "data": {
                    "version": current_version,
                    "patch": patch_data
                }
            }
            
            print(f"Sending patch: {patch_message}")
            await websocket.send(json.dumps(patch_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                print(f"Response: {response}")
                
                # Check if it's an error
                resp_data = json.loads(response)
                if resp_data.get("type") == "error":
                    print(f"❌ Error received: {resp_data['data']}")
                    return False
                else:
                    print("✅ Patch applied successfully!")
                    return True
                    
            except asyncio.TimeoutError:
                print("❌ Timeout waiting for response")
                return False
                
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_websocket_patch())
    if success:
        print("🎉 WebSocket patch test PASSED!")
    else:
        print("💥 WebSocket patch test FAILED!")