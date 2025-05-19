#!/bin/bash
# Login Test Script for Contract Management System

# Set base URL
BASE_URL="http://localhost:5000/v1"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Login Test ===${NC}"

# Test login with test user credentials
echo -e "${YELLOW}Testing login with test user credentials${NC}"
LOGIN_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"testuser@example.com","password":"password123"}' \
  $BASE_URL/auth/login)

# Print the response
echo "$LOGIN_RESPONSE"

# Check if login was successful
if [[ "$LOGIN_RESPONSE" == *"\"success\":true"* ]]; then
  echo -e "${GREEN}Login successful!${NC}"
  
  # Extract token
  TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.loads(sys.stdin.read()).get('token', ''))")
  
  if [ -n "$TOKEN" ]; then
    echo -e "${GREEN}Successfully retrieved auth token${NC}"
    echo "Token: ${TOKEN:0:20}..."
    
    # Test user profile endpoint with token
    echo -e "${YELLOW}Testing user profile endpoint${NC}"
    curl -s -X GET -H "Authorization: Bearer $TOKEN" $BASE_URL/auth/me
  fi
else
  echo -e "${RED}Login failed${NC}"
fi

echo -e "${BLUE}=== Login Test Complete ===${NC}"