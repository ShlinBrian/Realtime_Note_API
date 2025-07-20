#!/usr/bin/env python3
import asyncio
import websockets
import json
import base64

async def test_patch_only():
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
            
            # Send patch
            patch_content = {"title": "PATCH TEST", "content_md": "# Patch Test\n\nThis should work now!"}
            patch_data = base64.b64encode(json.dumps(patch_content).encode()).decode()
            
            patch_message = {
                "type": "patch",
                "data": {"version": version, "patch": patch_data}
            }
            
            print("Sending patch...")
            await websocket.send(json.dumps(patch_message))
            
            # Wait for responses
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3)
                    print(f"Response: {response}")
                    resp_data = json.loads(response)
                    if resp_data.get("type") == "debug":
                        print(f"✅ Debug response: received {resp_data['data']['received']}")
                    elif resp_data.get("type") == "error":
                        print(f"❌ Error: {resp_data['data']}")
                        break
                    elif resp_data.get("type") == "update":
                        print("✅ Update received - patch successful!")
                        break
                except asyncio.TimeoutError:
                    print("No more responses")
                    break
                    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_patch_only())