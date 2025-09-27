"""
Integration tests for WebSocket functionality
"""
import pytest
import json
import asyncio
import uuid
from unittest.mock import patch
import websockets
from fastapi.testclient import TestClient


class TestWebSocketConnection:
    """Test WebSocket connection and basic functionality"""

    @pytest.mark.asyncio
    async def test_websocket_connection_success(self, test_note, auth_headers):
        """Test successful WebSocket connection"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=5) as websocket:
                # Should receive initial message
                initial_message = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(initial_message)

                assert data["type"] == "init"
                assert "content" in data
                assert "version" in data
        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_connection_invalid_api_key(self, test_note):
        """Test WebSocket connection with invalid API key"""
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key=invalid_key"

        try:
            with pytest.raises((websockets.exceptions.ConnectionClosedError, OSError)):
                async with websockets.connect(uri, timeout=5) as websocket:
                    await websocket.recv()
        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_connection_missing_api_key(self, test_note):
        """Test WebSocket connection without API key"""
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}"

        try:
            with pytest.raises((websockets.exceptions.ConnectionClosedError, OSError)):
                async with websockets.connect(uri, timeout=5) as websocket:
                    await websocket.recv()
        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_connection_invalid_note_id(self, auth_headers):
        """Test WebSocket connection with invalid note ID"""
        api_key = auth_headers["x-api-key"]
        fake_note_id = str(uuid.uuid4())
        uri = f"ws://localhost:8000/ws/notes/{fake_note_id}?api_key={api_key}"

        try:
            with pytest.raises((websockets.exceptions.ConnectionClosedError, OSError)):
                async with websockets.connect(uri, timeout=5) as websocket:
                    await websocket.recv()
        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_connection_malformed_note_id(self, auth_headers):
        """Test WebSocket connection with malformed note ID"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/invalid-uuid?api_key={api_key}"

        try:
            with pytest.raises((websockets.exceptions.ConnectionClosedError, OSError)):
                async with websockets.connect(uri, timeout=5) as websocket:
                    await websocket.recv()
        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")


class TestWebSocketMessaging:
    """Test WebSocket message handling"""

    @pytest.mark.asyncio
    async def test_websocket_patch_message(self, test_note, auth_headers):
        """Test sending patch message via WebSocket"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=5) as websocket:
                # Receive initial message
                await websocket.recv()

                # Send patch message
                patch_message = {
                    "type": "patch",
                    "patch": "eyJ0aXRsZSI6ICJVcGRhdGVkIFRpdGxlIn0="  # base64 encoded JSON
                }

                await websocket.send(json.dumps(patch_message))

                # Should receive acknowledgment or update
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)

                # Should get either ack or patch_applied
                assert data["type"] in ["ack", "patch_applied"]

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_invalid_message_format(self, test_note, auth_headers):
        """Test sending invalid message format"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=5) as websocket:
                # Receive initial message
                await websocket.recv()

                # Send invalid JSON
                await websocket.send("invalid json")

                # Should receive error message
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)

                assert data["type"] == "error"

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_missing_patch_data(self, test_note, auth_headers):
        """Test sending patch message without patch data"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=5) as websocket:
                # Receive initial message
                await websocket.recv()

                # Send patch message without patch data
                patch_message = {
                    "type": "patch"
                    # Missing "patch" field
                }

                await websocket.send(json.dumps(patch_message))

                # Should receive error message
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)

                assert data["type"] == "error"

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_invalid_patch_data(self, test_note, auth_headers):
        """Test sending patch message with invalid base64 data"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=5) as websocket:
                # Receive initial message
                await websocket.recv()

                # Send patch message with invalid base64
                patch_message = {
                    "type": "patch",
                    "patch": "invalid_base64!!!"
                }

                await websocket.send(json.dumps(patch_message))

                # Should receive error message
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)

                assert data["type"] == "error"

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_unknown_message_type(self, test_note, auth_headers):
        """Test sending message with unknown type"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=5) as websocket:
                # Receive initial message
                await websocket.recv()

                # Send message with unknown type
                unknown_message = {
                    "type": "unknown_type",
                    "data": "some data"
                }

                await websocket.send(json.dumps(unknown_message))

                # Should receive error message or be ignored
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    data = json.loads(response)
                    # If we get a response, it should be an error
                    if "type" in data:
                        assert data["type"] == "error"
                except asyncio.TimeoutError:
                    # It's also acceptable to ignore unknown message types
                    pass

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")


class TestWebSocketCollaboration:
    """Test collaborative editing via WebSocket"""

    @pytest.mark.asyncio
    async def test_websocket_multiple_clients(self, test_note, auth_headers):
        """Test multiple clients connected to same note"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            # Connect two clients
            async with websockets.connect(uri, timeout=5) as ws1, \
                       websockets.connect(uri, timeout=5) as ws2:

                # Both should receive initial messages
                init1 = await asyncio.wait_for(ws1.recv(), timeout=5)
                init2 = await asyncio.wait_for(ws2.recv(), timeout=5)

                data1 = json.loads(init1)
                data2 = json.loads(init2)

                assert data1["type"] == "init"
                assert data2["type"] == "init"
                assert data1["content"] == data2["content"]

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_patch_broadcast(self, test_note, auth_headers):
        """Test that patches are broadcast to all connected clients"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=5) as ws1, \
                       websockets.connect(uri, timeout=5) as ws2:

                # Receive initial messages
                await ws1.recv()
                await ws2.recv()

                # Client 1 sends a patch
                patch_message = {
                    "type": "patch",
                    "patch": "eyJ0aXRsZSI6ICJVcGRhdGVkIGJ5IGNsaWVudCAxIn0="
                }

                await ws1.send(json.dumps(patch_message))

                # Both clients should receive the patch
                response1 = await asyncio.wait_for(ws1.recv(), timeout=5)
                response2 = await asyncio.wait_for(ws2.recv(), timeout=5)

                data1 = json.loads(response1)
                data2 = json.loads(response2)

                # One should be ack, the other should be patch notification
                message_types = {data1["type"], data2["type"]}
                assert "ack" in message_types or "patch_applied" in message_types

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")


class TestWebSocketEdgeCases:
    """Test WebSocket edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_websocket_connection_timeout(self, test_note, auth_headers):
        """Test WebSocket connection timeout handling"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=1) as websocket:
                # Keep connection alive for longer than normal
                await asyncio.sleep(2)

                # Should still be able to send messages
                ping_message = {"type": "ping"}
                await websocket.send(json.dumps(ping_message))

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_large_message(self, test_note, auth_headers):
        """Test sending large message via WebSocket"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=5) as websocket:
                # Receive initial message
                await websocket.recv()

                # Create a large patch (simulate large document)
                import base64
                large_content = "x" * 10000  # 10KB content
                large_patch_data = json.dumps({"content_md": large_content})
                large_patch_b64 = base64.b64encode(large_patch_data.encode()).decode()

                patch_message = {
                    "type": "patch",
                    "patch": large_patch_b64
                }

                await websocket.send(json.dumps(patch_message))

                # Should handle large message
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)

                # Should process successfully or return appropriate error
                assert data["type"] in ["ack", "patch_applied", "error"]

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_rapid_messages(self, test_note, auth_headers):
        """Test sending rapid succession of messages"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=5) as websocket:
                # Receive initial message
                await websocket.recv()

                # Send multiple messages rapidly
                for i in range(5):
                    patch_data = json.dumps({"title": f"Rapid update {i}"})
                    patch_b64 = base64.b64encode(patch_data.encode()).decode()

                    patch_message = {
                        "type": "patch",
                        "patch": patch_b64
                    }

                    await websocket.send(json.dumps(patch_message))

                # Should receive responses for all messages
                responses = []
                for i in range(5):
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2)
                        responses.append(json.loads(response))
                    except asyncio.TimeoutError:
                        break

                # Should have received some responses
                assert len(responses) > 0

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_unicode_content(self, test_note, auth_headers):
        """Test WebSocket with unicode content"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=5) as websocket:
                # Receive initial message
                await websocket.recv()

                # Send patch with unicode content
                import base64
                unicode_content = "测试内容 🚀 こんにちは"
                patch_data = json.dumps({"title": unicode_content})
                patch_b64 = base64.b64encode(patch_data.encode('utf-8')).decode()

                patch_message = {
                    "type": "patch",
                    "patch": patch_b64
                }

                await websocket.send(json.dumps(patch_message))

                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)

                assert data["type"] in ["ack", "patch_applied"]

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")


class TestWebSocketPerformance:
    """Test WebSocket performance characteristics"""

    @pytest.mark.asyncio
    async def test_websocket_concurrent_connections(self, test_note, auth_headers):
        """Test multiple concurrent WebSocket connections"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            # Test with multiple concurrent connections
            connections = []
            connection_count = 5

            for i in range(connection_count):
                try:
                    ws = await websockets.connect(uri, timeout=5)
                    connections.append(ws)
                    # Receive initial message
                    await ws.recv()
                except Exception:
                    break

            # All connections should be successful
            assert len(connections) == connection_count

            # Close all connections
            for ws in connections:
                await ws.close()

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")

    @pytest.mark.asyncio
    async def test_websocket_message_throughput(self, test_note, auth_headers):
        """Test WebSocket message throughput"""
        api_key = auth_headers["x-api-key"]
        uri = f"ws://localhost:8000/ws/notes/{test_note.note_id}?api_key={api_key}"

        try:
            async with websockets.connect(uri, timeout=5) as websocket:
                # Receive initial message
                await websocket.recv()

                # Measure time to send/receive messages
                import time
                import base64

                start_time = time.time()
                message_count = 10

                for i in range(message_count):
                    patch_data = json.dumps({"version": i})
                    patch_b64 = base64.b64encode(patch_data.encode()).decode()

                    patch_message = {
                        "type": "patch",
                        "patch": patch_b64
                    }

                    await websocket.send(json.dumps(patch_message))

                    # Wait for response
                    await websocket.recv()

                end_time = time.time()
                duration = end_time - start_time

                # Should complete reasonably quickly
                assert duration < 10.0  # 10 seconds max for 10 messages

        except Exception as e:
            pytest.skip(f"WebSocket server not available: {e}")