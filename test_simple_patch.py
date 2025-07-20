#!/usr/bin/env python3
import asyncio
import websockets
import json
import base64

async def test_simple_patch():
    note_id = "c7a3004a-1817-43d1-8d2a-33a15961f86b"
    api_key = "test123"
    
    uri = f"ws://localhost:8000/ws/notes/{note_id}?api_key={api_key}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected")
            
            # Get init message
            init_msg = await websocket.recv()
            init_data = json.loads(init_msg)
            version = init_data["data"]["version"]
            print(f"Current version: {version}")
            
            # Send simple patch
            patch_content = {"title": "New Title", "content_md": "New content"}
            patch_data = base64.b64encode(json.dumps(patch_content).encode()).decode()
            
            message = {
                "type": "patch",
                "data": {"version": version, "patch": patch_data}
            }
            
            print("Sending patch...")
            await websocket.send(json.dumps(message))
            print("Patch sent, waiting for response...")
            
            # Wait for any message with shorter timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3)
                print(f"Response: {response}")
            except asyncio.TimeoutError:
                print("❌ No response received")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_patch())