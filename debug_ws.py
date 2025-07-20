#!/usr/bin/env python3
import asyncio
import websockets
import json
import base64

async def debug_websocket():
    note_id = "c7a3004a-1817-43d1-8d2a-33a15961f86b"
    api_key = "test123"
    
    uri = f"ws://localhost:8000/ws/notes/{note_id}?api_key={api_key}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Check connection state
            print(f"WebSocket state: {websocket.state}")
            
            # Get init message
            init_msg = await websocket.recv()
            print(f"✅ Init message: {init_msg}")
            
            init_data = json.loads(init_msg)
            version = init_data["data"]["version"]
            print(f"Current version: {version}")
            
            # Check connection state after init
            print(f"WebSocket state after init: {websocket.state}")
            
            # Send a very simple message first
            simple_msg = {"type": "test", "data": {}}
            print(f"Sending test message: {simple_msg}")
            await websocket.send(json.dumps(simple_msg))
            print("Test message sent")
            
            # Wait a bit to see if connection is still alive
            await asyncio.sleep(1)
            print(f"WebSocket state after test: {websocket.state}")
            
            # Now try the patch
            patch_content = {"title": "Debug Test", "content_md": "Debug content"}
            patch_data = base64.b64encode(json.dumps(patch_content).encode()).decode()
            
            patch_message = {
                "type": "patch",
                "data": {
                    "version": version,
                    "patch": patch_data
                }
            }
            
            print(f"Sending patch: {patch_message}")
            await websocket.send(json.dumps(patch_message))
            print("Patch sent")
            
            # Check connection state
            print(f"WebSocket state after patch: {websocket.state}")
            
            # Wait for any response
            try:
                print("Waiting for response...")
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"✅ Response: {response}")
            except asyncio.TimeoutError:
                print("❌ Timeout - no response")
                print(f"Final WebSocket state: {websocket.state}")
            except Exception as e:
                print(f"❌ Error waiting for response: {e}")
                print(f"Final WebSocket state: {websocket.state}")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_websocket())