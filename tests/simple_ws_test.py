#!/usr/bin/env python3
import asyncio
import json

async def test_websocket_simple():
    try:
        import websockets
    except ImportError:
        print("websockets not available, trying manual test")
        return False
        
    note_id = "c7a3004a-1817-43d1-8d2a-33a15961f86b"
    api_key = "test123"
    
    uri = f"ws://localhost:8000/ws/notes/{note_id}?api_key={api_key}"
    
    try:
        print(f"Connecting to: {uri}")
        
        async with websockets.connect(uri, timeout=5) as websocket:
            print("✅ WebSocket connected successfully!")
            
            # Wait for initial message
            try:
                initial_message = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"✅ Received initial message: {initial_message}")
                
                # Try to parse the message
                msg_data = json.loads(initial_message)
                if msg_data.get("type") == "init":
                    print("✅ Init message received correctly")
                    return True
                else:
                    print(f"❌ Unexpected message type: {msg_data.get('type')}")
                    return False
                    
            except asyncio.TimeoutError:
                print("❌ Timeout waiting for initial message")
                return False
                
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_websocket_simple())
    if success:
        print("🎉 WebSocket test PASSED!")
    else:
        print("💥 WebSocket test FAILED!")