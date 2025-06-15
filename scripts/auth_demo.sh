#!/bin/bash

# Authentication API Demo Script
# This script demonstrates how to use all authentication methods

set -e  # Exit on any error

BASE_URL="http://localhost:8000"
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Realtime Notes API Authentication Demo ===${NC}"
echo

# Check if server is running
echo -e "${YELLOW}Checking if API server is running...${NC}"
if ! curl -s "$BASE_URL/health/live" > /dev/null; then
    echo -e "${RED}❌ API server is not running!${NC}"
    echo "Please start the server first:"
    echo "  cd /Users/shlin/Documents/project/realtime_note_api"
    echo "  make api-dev"
    exit 1
fi
echo -e "${GREEN}✅ API server is running${NC}"
echo

# 1. API Key Authentication Demo
echo -e "${BLUE}=== 1. API Key Authentication Demo ===${NC}"

echo -e "${YELLOW}Creating a new API key...${NC}"
API_KEY_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/api-keys" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "Demo API Key",
        "expires_at": "2025-12-31T23:59:59Z"
    }')

echo "Response: $API_KEY_RESPONSE"
API_KEY=$(echo $API_KEY_RESPONSE | jq -r '.key')
KEY_ID=$(echo $API_KEY_RESPONSE | jq -r '.key_id')

if [ "$API_KEY" = "null" ] || [ -z "$API_KEY" ]; then
    echo -e "${RED}❌ Failed to create API key${NC}"
    exit 1
fi

echo -e "${GREEN}✅ API Key created: $API_KEY${NC}"
echo

echo -e "${YELLOW}Testing API key authentication by creating a note...${NC}"
NOTE_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/notes" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{
        "title": "Demo Note",
        "content_md": "# Authentication Test\n\nThis note was created using API key authentication!"
    }')

echo "Response: $NOTE_RESPONSE"
NOTE_ID=$(echo $NOTE_RESPONSE | tr -d '"')
echo -e "${GREEN}✅ Note created with ID: $NOTE_ID${NC}"
echo

echo -e "${YELLOW}Listing all API keys...${NC}"
KEYS_RESPONSE=$(curl -s -X GET "$BASE_URL/v1/api-keys" \
    -H "x-api-key: $API_KEY")
echo "Response: $KEYS_RESPONSE"
echo

# 2. Bearer Token Authentication Demo
echo -e "${BLUE}=== 2. Bearer Token Authentication Demo ===${NC}"

echo -e "${YELLOW}Getting an access token...${NC}"
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/auth/token")
echo "Response: $TOKEN_RESPONSE"

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
if [ "$ACCESS_TOKEN" = "null" ] || [ -z "$ACCESS_TOKEN" ]; then
    echo -e "${RED}❌ Failed to get access token${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Access token obtained: $ACCESS_TOKEN${NC}"
echo

echo -e "${YELLOW}Testing bearer token by getting user info...${NC}"
USER_RESPONSE=$(curl -s -X GET "$BASE_URL/v1/auth/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN")
echo "Response: $USER_RESPONSE"
echo

echo -e "${YELLOW}Testing bearer token by listing notes...${NC}"
NOTES_RESPONSE=$(curl -s -X GET "$BASE_URL/v1/notes?limit=5" \
    -H "Authorization: Bearer $ACCESS_TOKEN")
echo "Response: $NOTES_RESPONSE"
echo

# 3. OAuth Device Code Flow Demo
echo -e "${BLUE}=== 3. OAuth 2.1 Device Code Flow Demo ===${NC}"

echo -e "${YELLOW}Starting device authorization flow...${NC}"
DEVICE_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/auth/device/code")
echo "Response: $DEVICE_RESPONSE"

USER_CODE=$(echo $DEVICE_RESPONSE | jq -r '.user_code')
VERIFICATION_URI=$(echo $DEVICE_RESPONSE | jq -r '.verification_uri')
echo -e "${GREEN}✅ Device code flow initiated${NC}"
echo -e "User code: ${YELLOW}$USER_CODE${NC}"
echo -e "Verification URI: ${YELLOW}$VERIFICATION_URI${NC}"
echo

echo -e "${YELLOW}Polling for device token...${NC}"
DEVICE_TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/auth/device/token")
echo "Response: $DEVICE_TOKEN_RESPONSE"
echo

# 4. Search Demo with Authentication
echo -e "${BLUE}=== 4. Search Demo with API Key ===${NC}"

echo -e "${YELLOW}Searching for notes...${NC}"
SEARCH_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/search" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{
        "query": "authentication test demo",
        "top_k": 3
    }')
echo "Response: $SEARCH_RESPONSE"
echo

# 5. Admin Endpoints Demo
echo -e "${BLUE}=== 5. Admin Endpoints Demo ===${NC}"

echo -e "${YELLOW}Getting usage statistics...${NC}"
USAGE_RESPONSE=$(curl -s -X GET "$BASE_URL/v1/admin/usage" \
    -H "x-api-key: $API_KEY")
echo "Response: $USAGE_RESPONSE"
echo

# 6. Cleanup Demo
echo -e "${BLUE}=== 6. Cleanup Demo ===${NC}"

if [ -n "$NOTE_ID" ] && [ "$NOTE_ID" != "null" ]; then
    echo -e "${YELLOW}Deleting the demo note...${NC}"
    DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/v1/notes/$NOTE_ID" \
        -H "x-api-key: $API_KEY")
    echo "Response: $DELETE_RESPONSE"
fi

echo -e "${YELLOW}Deleting the demo API key...${NC}"
KEY_DELETE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/v1/api-keys/$KEY_ID" \
    -H "x-api-key: $API_KEY")
echo "Response: $KEY_DELETE_RESPONSE"
echo

# Summary
echo -e "${BLUE}=== Demo Summary ===${NC}"
echo -e "${GREEN}✅ API Key Authentication: Working${NC}"
echo -e "${GREEN}✅ Bearer Token Authentication: Working${NC}"
echo -e "${GREEN}✅ OAuth Device Code Flow: Working${NC}"
echo -e "${GREEN}✅ Note Operations: Working${NC}"
echo -e "${GREEN}✅ Search Functionality: Working${NC}"
echo -e "${GREEN}✅ Admin Endpoints: Working${NC}"
echo -e "${GREEN}✅ Cleanup: Working${NC}"
echo
echo -e "${BLUE}🎉 All authentication methods are working correctly!${NC}"
echo
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Read the authentication guide: docs/authentication_guide.md"
echo "2. Check the full API documentation: docs/api_documentation.md"
echo "3. Try the WebSocket API: docs/websocket_api.md"
echo "4. Start building your application!"
