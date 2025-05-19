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

# Test 1: Login with email/password
echo -e "${YELLOW}Test 1: Login with email/password${NC}"
LOGIN_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123"}' \
  $BASE_URL/auth/login)
echo $LOGIN_RESPONSE | json_pp

# Extract token from login response for subsequent authenticated requests
AUTH_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)
if [ -n "$AUTH_TOKEN" ]; then
  echo -e "${GREEN}Successfully retrieved auth token${NC}"
else
  echo -e "${RED}Failed to get auth token${NC}"
fi

# Test 2: Sign up new user
echo -e "${YELLOW}Test 2: Sign up new user${NC}"
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com","password":"password123","name":"New Test User"}' \
  $BASE_URL/auth/signup | json_pp

# Test 3: Get current user profile
echo -e "${YELLOW}Test 3: Get current user profile${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/auth/me | json_pp

# Test 4: Forgot password
echo -e "${YELLOW}Test 4: Forgot password${NC}"
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com"}' \
  $BASE_URL/auth/forgot-password | json_pp

# Test 5: Social login (simulation, since we can't actually authenticate with Google/Microsoft here)
echo -e "${YELLOW}Test 5: Social login (simulation)${NC}"
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"provider":"google","token":"simulated_google_token"}' \
  $BASE_URL/auth/social-login | json_pp

echo -e "${BLUE}=== Authentication API Tests Complete ===${NC}"