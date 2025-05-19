#!/bin/bash
# Authentication API Testing Script for Contract Management System

# Set base URL
BASE_URL="http://localhost:5000/v1"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Authentication API Tests ===${NC}"

# Test 1: Sign up new user (create test account)
echo -e "${YELLOW}Test 1: Sign up new user${NC}"
SIGNUP_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"testuser-'$(date +%s)'@example.com","password":"password123","name":"Test User"}' \
  $BASE_URL/auth/signup)
echo "$SIGNUP_RESPONSE"

# Extract token from signup response
if [[ "$SIGNUP_RESPONSE" == *"token"* ]]; then
  echo -e "${GREEN}Successfully created user${NC}"
  # Extract token using a different method
  AUTH_TOKEN=$(echo "$SIGNUP_RESPONSE" | python3 -c "import sys, json; print(json.loads(sys.stdin.read()).get('token', ''))")
  if [ -n "$AUTH_TOKEN" ]; then
    echo -e "${GREEN}Successfully retrieved auth token${NC}"
    # Print first 20 chars of token for verification
    echo "Token: ${AUTH_TOKEN:0:20}..."
  else
    echo -e "${RED}Failed to extract token from response${NC}"
  fi
else
  echo -e "${RED}Failed to create user${NC}"
  AUTH_TOKEN=""
fi

# Test 2: Sign up with existing email (should fail)
echo -e "${YELLOW}Test 2: Sign up with existing email (should fail)${NC}"
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123","name":"Admin User"}' \
  $BASE_URL/auth/signup

# Test 3: Login with email/password
echo -e "${YELLOW}Test 3: Login with email/password${NC}"
LOGIN_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123"}' \
  $BASE_URL/auth/login)
echo "$LOGIN_RESPONSE"

# Extract token from login
LOGIN_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
if [ -n "$LOGIN_TOKEN" ]; then
  echo -e "${GREEN}Successfully logged in and retrieved auth token${NC}"
  # Use this token for subsequent requests
  AUTH_TOKEN=$LOGIN_TOKEN
fi

# Test 4: Get current user profile
echo -e "${YELLOW}Test 4: Get current user profile${NC}"
if [ -n "$AUTH_TOKEN" ]; then
  curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
    $BASE_URL/auth/me
else
  echo -e "${RED}Skipping test: No auth token available${NC}"
fi

# Test 5: Forgot password
echo -e "${YELLOW}Test 5: Forgot password${NC}"
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com"}' \
  $BASE_URL/auth/forgot-password

# Test 6: Social login (simulation)
echo -e "${YELLOW}Test 6: Social login (simulation)${NC}"
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"provider":"google","token":"simulated_google_token"}' \
  $BASE_URL/auth/social-login

echo -e "${BLUE}=== Authentication API Tests Complete ===${NC}"