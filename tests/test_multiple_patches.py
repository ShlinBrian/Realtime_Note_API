#!/usr/bin/env python3
import asyncio
import websockets
import json
import base64

async def test_multiple_patches():
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
            print(f"Starting version: {version}")
            
            # Test 3 patches
            for i in range(3):
                patch_content = {
                    "title": f"Test Title {i+1}", 
                    "content_md": f"# Test {i+1}\n\nThis is test patch number {i+1}!"
                }
                patch_data = base64.b64encode(json.dumps(patch_content).encode()).decode()
                
                patch_message = {
                    "type": "patch",
                    "data": {"version": version, "patch": patch_data}
                }
                
                print(f"\nSending patch {i+1}...")
                await websocket.send(json.dumps(patch_message))
                
                # Wait for response
                response = await websocket.recv()
                resp_data = json.loads(response)
                
                if resp_data.get("type") == "update":
                    version = resp_data["data"]["version"]
                    print(f"✅ Patch {i+1} successful! New version: {version}")
                    print(f"   Title: {resp_data['data']['title']}")
                elif resp_data.get("type") == "error":
                    print(f"❌ Patch {i+1} failed: {resp_data['data']}")
                    break
                    
            print(f"\nFinal version: {version}")
                    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_multiple_patches())