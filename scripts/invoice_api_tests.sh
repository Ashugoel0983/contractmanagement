#!/bin/bash
# Invoice API Testing Script for Contract Management System

# Set base URL
BASE_URL="http://localhost:5000/v1"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Invoice API Tests ===${NC}"

# First, login to get an authentication token
echo -e "${YELLOW}Authenticating with a newly created test user...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"invoice-test@example.com","password":"password123"}' \
  $BASE_URL/auth/signup)

# Extract token from login response
AUTH_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)
if [ -n "$AUTH_TOKEN" ]; then
  echo -e "${GREEN}Successfully retrieved auth token${NC}"
else
  echo -e "${RED}Failed to get auth token${NC}"
  echo -e "${RED}Unable to continue with invoice tests${NC}"
  exit 1
fi

# First create a contract to associate invoices with
echo -e "${YELLOW}Creating a test contract...${NC}"
CONTRACT_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "title": "Service Contract for Invoicing",
    "contract_type": "SERVICE_AGREEMENT",
    "description": "Test contract for invoice API testing",
    "start_date": "2025-05-01T00:00:00.000Z",
    "end_date": "2026-05-01T00:00:00.000Z",
    "value": 120000,
    "currency": "USD",
    "payment_terms": "Net 30",
    "tags": ["invoice", "test", "service"]
  }' \
  $BASE_URL/contracts)

# Extract contract ID for subsequent requests
CONTRACT_ID=$(echo $CONTRACT_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
if [ -n "$CONTRACT_ID" ]; then
  echo -e "${GREEN}Successfully created contract with ID $CONTRACT_ID${NC}"
else
  echo -e "${RED}Failed to get contract ID, using fallback value${NC}"
  # Use a fallback ID for testing
  CONTRACT_ID=1
fi

# Test 1: Get all invoices (empty at first)
echo -e "${YELLOW}Test 1: Get all invoices${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/invoices | json_pp

# Test 2: Configure invoice for the contract
echo -e "${YELLOW}Test 2: Configure invoice for contract${NC}"
INVOICE_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d "{
    \"contract_id\": $CONTRACT_ID,
    \"amount\": 10000,
    \"currency\": \"USD\",
    \"due_date\": \"2025-06-01T00:00:00.000Z\",
    \"is_recurring\": true,
    \"frequency\": \"monthly\",
    \"template_type\": \"standard\"
  }" \
  $BASE_URL/invoices/configure)
echo $INVOICE_RESPONSE | json_pp

# Extract invoice ID for subsequent requests
INVOICE_ID=$(echo $INVOICE_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
if [ -n "$INVOICE_ID" ]; then
  echo -e "${GREEN}Successfully created invoice with ID $INVOICE_ID${NC}"
else
  echo -e "${RED}Failed to get invoice ID, using fallback value${NC}"
  # Use a fallback ID for testing
  INVOICE_ID=1
fi

# Test 3: Get invoice details
echo -e "${YELLOW}Test 3: Get invoice details${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/invoices/$INVOICE_ID | json_pp

# Test 4: Regenerate invoice PDF
echo -e "${YELLOW}Test 4: Regenerate invoice PDF${NC}"
curl -s -X POST -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/invoices/$INVOICE_ID/regenerate | json_pp

# Test 5: Update invoice status
echo -e "${YELLOW}Test 5: Update invoice status${NC}"
curl -s -X PUT -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"status": "sent"}' \
  $BASE_URL/invoices/$INVOICE_ID/status | json_pp

# Test 6: Get all invoices (should see our new invoice)
echo -e "${YELLOW}Test 6: Get all invoices again${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/invoices | json_pp

# Test 7: Check for overdue invoices
echo -e "${YELLOW}Test 7: Check for overdue invoices${NC}"
curl -s -X POST -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/invoices/check-overdue | json_pp

echo -e "${BLUE}=== Invoice API Tests Complete ===${NC}"