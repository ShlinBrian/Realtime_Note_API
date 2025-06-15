# Realtime Notes API - Complete Documentation

## Overview

The Realtime Notes API is a comprehensive backend service for building collaborative note-taking applications with real-time editing, semantic search, and enterprise-grade features.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.example.com`

## Authentication

### API Key Authentication (Recommended)

```http
x-api-key: rk_your_api_key_here
```

### Bearer Token Authentication

```http
Authorization: Bearer your_access_token
```

---

## REST API Endpoints

### Notes Management

#### 1. Create Note

```http
POST /v1/notes
Content-Type: application/json
x-api-key: your_api_key

{
    "title": "My Note Title",
    "content_md": "# Hello World\n\nThis is **markdown** content."
}
```

**Request Body:**

1. title (required, string): Note title (1-200 characters)
2. content_md (required, string): Markdown content

**Response:** Note ID string

#### 2. Get Note

```http
GET /v1/notes/{note_id}
x-api-key: your_api_key
```

**Path Parameters:**

1. note_id (required, string): UUID of the note

**Response:** Complete note object with metadata

#### 3. Update Note

```http
PATCH /v1/notes/{note_id}
Content-Type: application/json
x-api-key: your_api_key

{
    "title": "Updated Title",
    "content_md": "# Updated Content"
}
```

**Path Parameters:**

1. note_id (required, string): UUID of the note

**Request Body (all optional):**

1. title (optional, string): New title
2. content_md (optional, string): New content

**Response:** Version number object

#### 4. Delete Note

```http
DELETE /v1/notes/{note_id}
x-api-key: your_api_key
```

**Path Parameters:**

1. note_id (required, string): UUID of the note

**Response:** Deletion confirmation

#### 5. List Notes

```http
GET /v1/notes?skip=0&limit=10
x-api-key: your_api_key
```

**Query Parameters:**

1. skip (optional, integer): Items to skip (default: 0)
2. limit (optional, integer): Max items to return (default: 100, max: 1000)

**Response:** Array of note objects

### Search

#### 6. Search Notes

```http
POST /v1/search
Content-Type: application/json
x-api-key: your_api_key

{
    "query": "machine learning algorithms",
    "top_k": 5
}
```

**Request Body:**

1. query (required, string): Search query
2. top_k (optional, integer): Max results (default: 10, max: 100)

**Response:** Array of search results with scores

#### 7. Rebuild Search Index

```http
POST /v1/search/rebuild
x-api-key: your_api_key
```

**Response:** Index rebuild status

### API Key Management

#### 8. Create API Key

```http
POST /v1/api-keys
Content-Type: application/json

{
    "name": "Production Key",
    "expires_at": "2025-12-31T23:59:59Z"
}
```

**Request Body:**

1. name (required, string): Key description (1-100 characters)
2. expires_at (optional, datetime): Expiration date (ISO format)

**Response:** API key object (secret shown once)

#### 9. List API Keys

```http
GET /v1/api-keys
x-api-key: your_api_key
```

**Response:** Array of API key info (no secrets)

#### 10. Delete API Key

```http
DELETE /v1/api-keys/{key_id}
x-api-key: your_api_key
```

**Path Parameters:**

1. key_id (required, string): UUID of the API key

**Response:** Deletion confirmation

### Authentication

#### 11. Get Access Token

```http
POST /v1/auth/token
Content-Type: application/json
```

**Response:** Bearer token for authentication

#### 12. Device Code Flow - Start

```http
POST /v1/auth/device/code
Content-Type: application/json
```

**Response:** Device code and verification URI

#### 13. Device Code Flow - Token

```http
POST /v1/auth/device/token
Content-Type: application/json
```

**Response:** Access token once authorized

#### 14. Get Current User

```http
GET /v1/auth/me
Authorization: Bearer your_token
```

**Response:** Current user information

### Administration

#### 15. Get Usage Statistics

```http
GET /v1/admin/usage?from=2024-01-01&to=2024-01-31
x-api-key: your_api_key
```

**Query Parameters:**

1. from (optional, date): Start date (YYYY-MM-DD, default: 30 days ago)
2. to (optional, date): End date (YYYY-MM-DD, default: today)

**Response:** Array of daily usage summaries

---

## WebSocket API

### Real-time Collaboration

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/notes/{note_id}");

// Send patch
ws.send(
  JSON.stringify({
    patch: btoa(
      JSON.stringify([{ op: "replace", path: "/title", value: "New Title" }])
    ),
    version: 1,
  })
);

// Receive patches
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Received patch:", data);
};
```

**Connection:**

- **URL**: `ws://localhost:8000/ws/notes/{note_id}`
- **Headers**: Optional x-api-key for authentication

**Message Format:**

```json
{
  "patch": "base64_encoded_json_patch",
  "version": 123
}
```

**JSON Patch Operations:**

- `replace`: Update field value
- `add`: Add new content
- `remove`: Remove content

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "404",
    "message": "Note not found"
  }
}
```

**Common HTTP Status Codes:**

- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error

---

## Rate Limits

| API Type  | Limit                |
| --------- | -------------------- |
| REST API  | 1000 requests/minute |
| WebSocket | 100 messages/minute  |
| Search    | 100 queries/minute   |

Rate limit headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

---

## Data Models

### Note Object

```json
{
  "note_id": "uuid",
  "title": "string",
  "content_md": "string",
  "version": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Search Result

```json
{
  "note_id": "uuid",
  "score": 0.95
}
```

### API Key

```json
{
  "key_id": "uuid",
  "name": "string",
  "key": "rk_secret_key",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2025-01-15T10:30:00Z"
}
```

---

## SDK Examples

### cURL

```bash
# Create a note
curl -X POST "http://localhost:8000/v1/notes" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Note", "content_md": "# Hello World"}'

# Search notes
curl -X POST "http://localhost:8000/v1/search" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "hello world", "top_k": 5}'
```

### Python

```python
import requests

# Create client
api_key = "your_api_key"
base_url = "http://localhost:8000"
headers = {"x-api-key": api_key}

# Create note
response = requests.post(
    f"{base_url}/v1/notes",
    headers=headers,
    json={"title": "Test Note", "content_md": "# Hello World"}
)
note_id = response.text.strip('"')

# Search notes
response = requests.post(
    f"{base_url}/v1/search",
    headers=headers,
    json={"query": "hello", "top_k": 5}
)
results = response.json()
```

### JavaScript

```javascript
const apiKey = "your_api_key";
const baseUrl = "http://localhost:8000";

// Create note
const response = await fetch(`${baseUrl}/v1/notes`, {
  method: "POST",
  headers: {
    "x-api-key": apiKey,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    title: "Test Note",
    content_md: "# Hello World",
  }),
});
const noteId = await response.text();

// Search notes
const searchResponse = await fetch(`${baseUrl}/v1/search`, {
  method: "POST",
  headers: {
    "x-api-key": apiKey,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    query: "hello",
    top_k: 5,
  }),
});
const results = await searchResponse.json();
```

---

## Deployment

The API is designed for Kubernetes deployment with:

- Horizontal scaling
- Database persistence
- Redis for WebSocket coordination
- Health checks and monitoring
- Helm charts included

See the README.md for complete deployment instructions.
