# How to Use the Authentication APIs

The Realtime Notes API provides two main authentication methods:

## 1. API Key Authentication (Recommended)

### Step 1: Create an API Key

First, create an API key using the API keys endpoint:

```bash
curl -X POST "http://localhost:8000/v1/api-keys" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My API Key",
    "expires_at": "2025-12-31T23:59:59Z"
  }'
```

**Response:**

```json
{
  "key_id": "key_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "My API Key",
  "key": "rk_1234567890abcdef1234567890abcdef",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

**⚠️ Important:** Save the `key` value immediately - it won't be shown again!

### Step 2: Use the API Key

Include the API key in the `x-api-key` header for all subsequent requests:

```bash
curl -X GET "http://localhost:8000/v1/notes" \
  -H "x-api-key: rk_1234567890abcdef1234567890abcdef"
```

### Step 3: Manage API Keys

**List all your API keys:**

```bash
curl -X GET "http://localhost:8000/v1/api-keys" \
  -H "x-api-key: your_api_key"
```

**Delete an API key:**

```bash
curl -X DELETE "http://localhost:8000/v1/api-keys/key_a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -H "x-api-key: your_api_key"
```

## 2. Bearer Token Authentication (Demo)

### Step 1: Get an Access Token

```bash
curl -X POST "http://localhost:8000/v1/auth/token" \
  -H "Content-Type: application/json"
```

**Response:**

```json
{
  "access_token": "dummy_token",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Step 2: Use the Bearer Token

Include the token in the `Authorization` header:

```bash
curl -X GET "http://localhost:8000/v1/notes" \
  -H "Authorization: Bearer dummy_token"
```

### Step 3: Get User Information

```bash
curl -X GET "http://localhost:8000/v1/auth/me" \
  -H "Authorization: Bearer dummy_token"
```

**Response:**

```json
{
  "user_id": "default_user",
  "email": "user@example.com",
  "role": "admin",
  "org_id": "default",
  "created_at": "2023-01-01T00:00:00Z"
}
```

## 3. OAuth 2.1 Device Code Flow (Demo)

### Step 1: Start Device Authorization

```bash
curl -X POST "http://localhost:8000/v1/auth/device/code"
```

**Response:**

```json
{
  "device_code": "dummy_device_code",
  "user_code": "ABCD-1234",
  "verification_uri": "https://example.com/verify",
  "expires_in": 1800,
  "interval": 5
}
```

### Step 2: User Authorization

1. Direct the user to the `verification_uri`
2. User enters the `user_code` on the verification page
3. User authorizes the application

### Step 3: Poll for Token

Poll the token endpoint at the specified interval:

```bash
curl -X POST "http://localhost:8000/v1/auth/device/token"
```

**Response (once authorized):**

```json
{
  "access_token": "dummy_token",
  "token_type": "bearer",
  "expires_in": 1800
}
```

## Complete Usage Examples

### Example 1: Full API Key Workflow

```bash
# 1. Create an API key
API_KEY_RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/api-keys" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Key"}')

# 2. Extract the key from response
API_KEY=$(echo $API_KEY_RESPONSE | jq -r '.key')

# 3. Create a note using the API key
curl -X POST "http://localhost:8000/v1/notes" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "title": "My First Note",
    "content_md": "# Hello World\n\nThis is my first note!"
  }'

# 4. List notes
curl -X GET "http://localhost:8000/v1/notes" \
  -H "x-api-key: $API_KEY"

# 5. Search notes
curl -X POST "http://localhost:8000/v1/search" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "query": "hello world",
    "top_k": 5
  }'
```

### Example 2: Bearer Token Workflow

```bash
# 1. Get access token
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/v1/auth/token")
ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

# 2. Use token to access protected endpoints
curl -X GET "http://localhost:8000/v1/notes" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# 3. Get user info
curl -X GET "http://localhost:8000/v1/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Authentication Methods Comparison

| Method               | Best For                           | Security                        | Expiration             |
| -------------------- | ---------------------------------- | ------------------------------- | ---------------------- |
| **API Keys**         | Server-to-server, long-term access | High (cryptographically secure) | Optional, configurable |
| **Bearer Tokens**    | User sessions, temporary access    | Medium (demo implementation)    | Fixed 30 minutes       |
| **Device Code Flow** | IoT devices, CLI tools             | High (OAuth 2.1 standard)       | Configurable           |

## Security Best Practices

1. **API Keys:**

   - Store in environment variables, not in code
   - Use different keys for different environments
   - Rotate keys regularly
   - Set expiration dates

2. **Bearer Tokens:**

   - Store securely in memory
   - Implement token refresh logic
   - Clear tokens on logout

3. **General:**
   - Always use HTTPS in production
   - Monitor for unusual API usage
   - Implement rate limiting
   - Log authentication events

## Error Handling

Common authentication errors:

```json
{
  "error": {
    "code": "401",
    "message": "Invalid API key"
  }
}
```

```json
{
  "error": {
    "code": "401",
    "message": "Token expired"
  }
}
```

## Quick Start Script

Save this as `auth_test.sh`:

```bash
#!/bin/bash

# Test API authentication
BASE_URL="http://localhost:8000"

echo "Creating API key..."
API_KEY_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/api-keys" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Key"}')

API_KEY=$(echo $API_KEY_RESPONSE | jq -r '.key')
echo "API Key: $API_KEY"

echo "Testing API key authentication..."
curl -X GET "$BASE_URL/v1/notes" \
  -H "x-api-key: $API_KEY"

echo "Getting bearer token..."
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/auth/token")
ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
echo "Access Token: $ACCESS_TOKEN"

echo "Testing bearer token authentication..."
curl -X GET "$BASE_URL/v1/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Run with: `chmod +x auth_test.sh && ./auth_test.sh`
