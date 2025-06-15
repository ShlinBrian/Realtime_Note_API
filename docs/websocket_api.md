# WebSocket API Documentation

## Real-time Note Collaboration

The WebSocket API enables real-time collaborative editing of notes using Conflict-free Replicated Data Types (CRDT) for seamless multi-user collaboration.

### Connection Endpoint

```
WebSocket: /ws/notes/{note_id}
```

**Description:** Establish a WebSocket connection for real-time collaborative editing of a specific note.

**Path Parameters:**

1. note_id (required, string): The UUID of the note to collaborate on

**Headers:**

- Upgrade: websocket (required)
- Connection: Upgrade (required)
- Sec-WebSocket-Key: <key> (required)
- Sec-WebSocket-Version: 13 (required)

**Query Parameters:** None

### Message Format

All WebSocket messages use JSON format with the following structure:

#### Outgoing Messages (Client → Server)

```json
{
  "patch": "base64_encoded_json_patch",
  "version": 123
}
```

**Fields:**

- patch (required, string): Base64-encoded JSON patch using RFC 6902 format
- version (required, integer): Current version number for optimistic concurrency control

#### Incoming Messages (Server → Client)

```json
{
  "type": "patch",
  "patch": "base64_encoded_json_patch",
  "version": 124,
  "user_id": "user_123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Fields:**

- type: Message type ("patch", "presence", "error")
- patch: Base64-encoded JSON patch to apply
- version: New version number after applying patch
- user_id: ID of user who made the change
- timestamp: When the change was made

### Connection Flow

1. **Connect**: Open WebSocket connection to `/ws/notes/{note_id}`
2. **Authentication**: Optionally provide API key in connection headers
3. **Sync**: Receive current note state and version
4. **Collaborate**: Send and receive patches in real-time
5. **Disconnect**: Close connection when done

### Example Usage

#### JavaScript Client

```javascript
const noteId = "a1b2c3d4-e5f6-7890-abcd-ef1234567890";
const ws = new WebSocket(`ws://localhost:8000/ws/notes/${noteId}`);

// Handle connection
ws.onopen = function (event) {
  console.log("Connected to note collaboration");
};

// Handle incoming patches
ws.onmessage = function (event) {
  const message = JSON.parse(event.data);

  if (message.type === "patch") {
    // Decode and apply patch
    const patch = JSON.parse(atob(message.patch));
    applyPatchToNote(patch);
    currentVersion = message.version;
  }
};

// Send a patch
function sendPatch(jsonPatch) {
  const encodedPatch = btoa(JSON.stringify(jsonPatch));
  const message = {
    patch: encodedPatch,
    version: currentVersion,
  };
  ws.send(JSON.stringify(message));
}

// Example patch for title change
const titlePatch = [
  {
    op: "replace",
    path: "/title",
    value: "New Title",
  },
];
sendPatch(titlePatch);
```

#### Python Client

```python
import asyncio
import websockets
import json
import base64

async def collaborate_on_note(note_id):
    uri = f"ws://localhost:8000/ws/notes/{note_id}"

    async with websockets.connect(uri) as websocket:
        # Send a patch
        patch = [{"op": "replace", "path": "/content_md", "value": "# Updated content"}]
        encoded_patch = base64.b64encode(json.dumps(patch).encode()).decode()

        message = {
            "patch": encoded_patch,
            "version": 1
        }

        await websocket.send(json.dumps(message))

        # Listen for responses
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

# Run the client
asyncio.run(collaborate_on_note("your-note-id"))
```

### JSON Patch Operations

The WebSocket API uses RFC 6902 JSON Patch format for all modifications:

#### Supported Operations

1. **Replace**: Update a field value

```json
{ "op": "replace", "path": "/title", "value": "New Title" }
```

2. **Add**: Add new content

```json
{ "op": "add", "path": "/content_md", "value": "Additional content" }
```

3. **Remove**: Remove content

```json
{ "op": "remove", "path": "/some_field" }
```

#### Common Patch Examples

**Change title:**

```json
[{ "op": "replace", "path": "/title", "value": "My Updated Note" }]
```

**Update content:**

```json
[
  {
    "op": "replace",
    "path": "/content_md",
    "value": "# New Content\n\nUpdated text."
  }
]
```

**Multiple changes:**

```json
[
  { "op": "replace", "path": "/title", "value": "Updated Title" },
  {
    "op": "replace",
    "path": "/content_md",
    "value": "# Updated\n\nNew content."
  }
]
```

### Error Handling

#### Connection Errors

- **404**: Note not found
- **403**: Access denied
- **500**: Server error

#### Message Errors

```json
{
  "type": "error",
  "error": "version_conflict",
  "message": "Version conflict detected. Please refresh and try again.",
  "current_version": 125
}
```

**Common Error Types:**

- `version_conflict`: Client version doesn't match server version
- `invalid_patch`: Malformed JSON patch
- `access_denied`: Insufficient permissions
- `note_not_found`: Note has been deleted

### Conflict Resolution

The WebSocket API uses CRDT (Conflict-free Replicated Data Types) for automatic conflict resolution:

1. **Optimistic Updates**: Apply changes immediately on client
2. **Version Tracking**: Each change increments version number
3. **Automatic Merging**: Server merges conflicting changes
4. **Broadcast**: Changes are broadcast to all connected clients

### Performance Features

- **Connection Pooling**: Multiple clients per note
- **Redis Pub/Sub**: Scalable message distribution
- **Batch Processing**: Multiple patches in single message
- **Compression**: Efficient binary encoding
- **Rate Limiting**: Per-connection rate limits

### Security

- **API Key Authentication**: Optional authentication via headers
- **Organization Isolation**: Users only see notes from their organization
- **Input Validation**: All patches are validated before application
- **Rate Limiting**: Prevents abuse and spam

### Monitoring

The WebSocket API tracks:

- Active connections per note
- Messages sent/received per connection
- Bandwidth usage
- Connection duration
- Error rates

### Best Practices

1. **Handle Disconnections**: Implement reconnection logic
2. **Version Tracking**: Always track current version
3. **Error Recovery**: Handle version conflicts gracefully
4. **Rate Limiting**: Don't send patches too frequently
5. **Batch Changes**: Group related changes in single patch
6. **Validate Patches**: Ensure patches are well-formed
7. **Security**: Use API keys for authentication
8. **Cleanup**: Close connections when done
