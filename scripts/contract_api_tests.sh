#!/bin/bash
# Contract API Testing Script for Contract Management System

# Set base URL
BASE_URL="http://localhost:5000/v1"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Contract API Tests ===${NC}"

# First, login to get an authentication token
echo -e "${YELLOW}Authenticating with a newly created test user...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"contract-test@example.com","password":"password123"}' \
  $BASE_URL/auth/signup)

# Extract token from login response
AUTH_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)
if [ -n "$AUTH_TOKEN" ]; then
  echo -e "${GREEN}Successfully retrieved auth token${NC}"
else
  echo -e "${RED}Failed to get auth token${NC}"
  echo -e "${RED}Unable to continue with contract tests${NC}"
  exit 1
fi

# Test 1: Get all contracts (empty at first)
echo -e "${YELLOW}Test 1: Get all contracts${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts | json_pp

# Test 2: Create a new contract
echo -e "${YELLOW}Test 2: Create a new contract${NC}"
CONTRACT_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "title": "Software Development Agreement",
    "contract_type": "SERVICE_AGREEMENT",
    "description": "Agreement for development of contract management system",
    "start_date": "2025-05-01T00:00:00.000Z",
    "end_date": "2026-05-01T00:00:00.000Z",
    "value": 75000,
    "currency": "USD",
    "payment_terms": "Net 30",
    "tags": ["software", "development", "service"]
  }' \
  $BASE_URL/contracts)
echo $CONTRACT_RESPONSE | json_pp

# Extract contract ID for subsequent requests
CONTRACT_ID=$(echo $CONTRACT_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
if [ -n "$CONTRACT_ID" ]; then
  echo -e "${GREEN}Successfully created contract with ID $CONTRACT_ID${NC}"
else
  echo -e "${RED}Failed to get contract ID, using fallback value${NC}"
  # Use a fallback ID for testing
  CONTRACT_ID=1
fi

# Test 3: Get contract details
echo -e "${YELLOW}Test 3: Get contract details${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts/$CONTRACT_ID | json_pp

# Test 4: Update contract
echo -e "${YELLOW}Test 4: Update contract${NC}"
curl -s -X PUT -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "title": "Updated Software Development Agreement",
    "description": "Updated agreement for development of contract management system",
    "value": 85000
  }' \
  $BASE_URL/contracts/$CONTRACT_ID | json_pp

# Test 5: Get contract metrics
echo -e "${YELLOW}Test 5: Get contract metrics${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts/metrics | json_pp

# Test 6: Extract contract data (for AI processing)
echo -e "${YELLOW}Test 6: Extract contract data${NC}"
curl -s -X POST -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts/$CONTRACT_ID/extract | json_pp

# Test 7: Get extracted data
echo -e "${YELLOW}Test 7: Get extracted data${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts/$CONTRACT_ID/extracted-data | json_pp

# Test 8: Add parties to contract
echo -e "${YELLOW}Test 8: Add parties to contract${NC}"
PARTY_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "party_type": "client",
    "legal_name": "Acme Corporation",
    "address": "123 Main St, San Francisco, CA",
    "contact_person": "John Doe",
    "email": "john@acme.com",
    "phone": "+1-555-123-4567"
  }' \
  $BASE_URL/contracts/$CONTRACT_ID/parties)
echo $PARTY_RESPONSE | json_pp

# Test 9: Delete contract
echo -e "${YELLOW}Test 9: Delete contract${NC}"
curl -s -X DELETE -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts/$CONTRACT_ID | json_pp

echo -e "${BLUE}=== Contract API Tests Complete ===${NC}"