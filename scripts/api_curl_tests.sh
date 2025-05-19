#!/bin/bash
# API Testing Script for Contract Management System using curl
# This script provides curl commands for testing all endpoints

# Set base URL
BASE_URL="http://localhost:5000/v1"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Contract Management System API Test Script ===${NC}"
echo -e "${YELLOW}Saving access token in AUTH_TOKEN variable for authenticated requests${NC}"
echo ""

# ===== Authentication API Tests =====
echo -e "${BLUE}=== Authentication API Tests ===${NC}"

# Test Login API
echo -e "${YELLOW}Testing Login API...${NC}"
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

# Test Signup API
echo -e "${YELLOW}Testing Signup API...${NC}"
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com","password":"password123","name":"New Test User"}' \
  $BASE_URL/auth/signup | json_pp

# Test Me API (get current user profile)
echo -e "${YELLOW}Testing Me API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/auth/me | json_pp

# Test Forgot Password API
echo -e "${YELLOW}Testing Forgot Password API...${NC}"
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com"}' \
  $BASE_URL/auth/forgot-password | json_pp

# ===== Contract API Tests =====
echo -e "${BLUE}=== Contract API Tests ===${NC}"

# Test Get All Contracts
echo -e "${YELLOW}Testing Get All Contracts API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts | json_pp

# Test Create Contract
echo -e "${YELLOW}Testing Create Contract API...${NC}"
CONTRACT_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "title": "Sample Contract via API",
    "contract_type": "SERVICE_AGREEMENT",
    "description": "This is a test contract created via API",
    "start_date": "2025-05-01T00:00:00.000Z",
    "end_date": "2026-05-01T00:00:00.000Z",
    "value": 75000,
    "currency": "USD",
    "payment_terms": "Net 30",
    "tags": ["test", "api", "sample"]
  }' \
  $BASE_URL/contracts)
echo $CONTRACT_RESPONSE | json_pp

# Extract contract ID from create response for subsequent requests
CONTRACT_ID=$(echo $CONTRACT_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
if [ -n "$CONTRACT_ID" ]; then
  echo -e "${GREEN}Successfully created contract with ID $CONTRACT_ID${NC}"
else
  echo -e "${RED}Failed to get contract ID${NC}"
  # Use a fallback ID for testing
  CONTRACT_ID=1
fi

# Test Get Contract Details
echo -e "${YELLOW}Testing Get Contract Details API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts/$CONTRACT_ID | json_pp

# Test Update Contract
echo -e "${YELLOW}Testing Update Contract API...${NC}"
curl -s -X PUT -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "title": "Updated Contract Title",
    "description": "This contract was updated via API",
    "value": 85000
  }' \
  $BASE_URL/contracts/$CONTRACT_ID | json_pp

# Test Delete Contract
echo -e "${YELLOW}Testing Delete Contract API...${NC}"
curl -s -X DELETE -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts/$CONTRACT_ID | json_pp

# Test Get Contract Metrics
echo -e "${YELLOW}Testing Get Contract Metrics API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts/metrics | json_pp

# Test Extract Contract Data
echo -e "${YELLOW}Testing Extract Contract Data API...${NC}"
curl -s -X POST -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts/$CONTRACT_ID/extract | json_pp

# ===== AI API Tests =====
echo -e "${BLUE}=== AI API Tests ===${NC}"

# Test Extract Document API
echo -e "${YELLOW}Testing Extract Document API...${NC}"
curl -s -X POST -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "file=@/path/to/sample.pdf" \
  $BASE_URL/ai/extract | json_pp

# Test Analyze Clauses API
echo -e "${YELLOW}Testing Analyze Clauses API...${NC}"
curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "contract_text": "This agreement, dated May 1, 2025, between Company A and Company B...",
    "contract_type": "SERVICE_AGREEMENT"
  }' \
  $BASE_URL/ai/analyze-clauses | json_pp

# Test Analyze Risk API
echo -e "${YELLOW}Testing Analyze Risk API...${NC}"
curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "contract_id": '$CONTRACT_ID'
  }' \
  $BASE_URL/ai/analyze-risk | json_pp

# ===== Invoice API Tests =====
echo -e "${BLUE}=== Invoice API Tests ===${NC}"

# Test Get All Invoices
echo -e "${YELLOW}Testing Get All Invoices API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/invoices | json_pp

# Test Configure Invoice
echo -e "${YELLOW}Testing Configure Invoice API...${NC}"
INVOICE_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "contract_id": '$CONTRACT_ID',
    "amount": 15000,
    "currency": "USD",
    "due_date": "2025-06-01T00:00:00.000Z",
    "is_recurring": true,
    "frequency": "monthly",
    "template_type": "standard"
  }' \
  $BASE_URL/invoices/configure)
echo $INVOICE_RESPONSE | json_pp

# Extract invoice ID from response
INVOICE_ID=$(echo $INVOICE_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
if [ -n "$INVOICE_ID" ]; then
  echo -e "${GREEN}Successfully created invoice with ID $INVOICE_ID${NC}"
else
  echo -e "${RED}Failed to get invoice ID${NC}"
  # Use a fallback ID for testing
  INVOICE_ID=1
fi

# Test Get Invoice Details
echo -e "${YELLOW}Testing Get Invoice Details API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/invoices/$INVOICE_ID | json_pp

# Test Regenerate Invoice
echo -e "${YELLOW}Testing Regenerate Invoice API...${NC}"
curl -s -X POST -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/invoices/$INVOICE_ID/regenerate | json_pp

# Test Update Invoice Status
echo -e "${YELLOW}Testing Update Invoice Status API...${NC}"
curl -s -X PUT -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{"status": "paid"}' \
  $BASE_URL/invoices/$INVOICE_ID/status | json_pp

# Test Check Overdue Invoices
echo -e "${YELLOW}Testing Check Overdue Invoices API...${NC}"
curl -s -X POST -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/invoices/check-overdue | json_pp

# ===== Approval API Tests =====
echo -e "${BLUE}=== Approval API Tests ===${NC}"

# Test Get Pending Approvals
echo -e "${YELLOW}Testing Get Pending Approvals API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/approvals/pending | json_pp

# Test Submit For Approval
echo -e "${YELLOW}Testing Submit For Approval API...${NC}"
APPROVAL_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "contract_id": '$CONTRACT_ID'
  }' \
  $BASE_URL/approvals/submit)
echo $APPROVAL_RESPONSE | json_pp

# Extract approval ID from response
APPROVAL_ID=$(echo $APPROVAL_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
if [ -n "$APPROVAL_ID" ]; then
  echo -e "${GREEN}Successfully created approval with ID $APPROVAL_ID${NC}"
else
  echo -e "${RED}Failed to get approval ID${NC}"
  # Use a fallback ID for testing
  APPROVAL_ID=1
fi

# Test Approve Contract
echo -e "${YELLOW}Testing Approve Contract API...${NC}"
curl -s -X PUT -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "comments": "Approved via API test"
  }' \
  $BASE_URL/approvals/$APPROVAL_ID/approve | json_pp

# Test Reject Contract
echo -e "${YELLOW}Testing Reject Contract API...${NC}"
curl -s -X PUT -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "comments": "Rejected via API test"
  }' \
  $BASE_URL/approvals/$APPROVAL_ID/reject | json_pp

# Test Get Approval
echo -e "${YELLOW}Testing Get Approval API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/approvals/$APPROVAL_ID | json_pp

# ===== Notification API Tests =====
echo -e "${BLUE}=== Notification API Tests ===${NC}"

# Test Get Notifications
echo -e "${YELLOW}Testing Get Notifications API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/notifications | json_pp

# Test Create Notification (for testing purposes)
echo -e "${YELLOW}Testing Create Notification API...${NC}"
NOTIFICATION_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "message": "Test notification via API",
    "type": "SYSTEM",
    "contract_id": '$CONTRACT_ID'
  }' \
  $BASE_URL/notifications)
echo $NOTIFICATION_RESPONSE | json_pp

# Extract notification ID from response
NOTIFICATION_ID=$(echo $NOTIFICATION_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
if [ -n "$NOTIFICATION_ID" ]; then
  echo -e "${GREEN}Successfully created notification with ID $NOTIFICATION_ID${NC}"
else
  echo -e "${RED}Failed to get notification ID${NC}"
  # Use a fallback ID for testing
  NOTIFICATION_ID=1
fi

# Test Mark Notification Read
echo -e "${YELLOW}Testing Mark Notification Read API...${NC}"
curl -s -X PUT -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/notifications/$NOTIFICATION_ID/read | json_pp

# Test Mark All Notifications Read
echo -e "${YELLOW}Testing Mark All Notifications Read API...${NC}"
curl -s -X PUT -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/notifications/read-all | json_pp

# Test Check Expiring Contracts
echo -e "${YELLOW}Testing Check Expiring Contracts API...${NC}"
curl -s -X POST -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/notifications/check-expiring | json_pp

# ===== Search API Tests =====
echo -e "${BLUE}=== Search API Tests ===${NC}"

# Test Search Contracts
echo -e "${YELLOW}Testing Search Contracts API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  "$BASE_URL/contracts/search?query=sample&status=ACTIVE&type=SERVICE_AGREEMENT&sort_by=created_at&sort_order=desc" | json_pp

# Test Get All Tags
echo -e "${YELLOW}Testing Get All Tags API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts/search/tags | json_pp

# Test Get Search Filters
echo -e "${YELLOW}Testing Get Search Filters API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/contracts/search/filters | json_pp

# ===== Settings API Tests =====
echo -e "${BLUE}=== Settings API Tests ===${NC}"

# Test Get Role Access Matrix
echo -e "${YELLOW}Testing Get Role Access Matrix API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/settings/roles | json_pp

# Test Update Role Matrix
echo -e "${YELLOW}Testing Update Role Matrix API...${NC}"
curl -s -X PUT -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "ADMIN": {
      "contracts": ["read", "write", "delete", "approve"],
      "users": ["read", "write", "delete"],
      "invoices": ["read", "write", "delete"],
      "settings": ["read", "write"]
    },
    "MANAGER": {
      "contracts": ["read", "write", "approve"],
      "users": ["read"],
      "invoices": ["read", "write"],
      "settings": ["read"]
    },
    "USER": {
      "contracts": ["read", "write"],
      "users": ["read"],
      "invoices": ["read"],
      "settings": ["read"]
    }
  }' \
  $BASE_URL/settings/roles | json_pp

# Test Get User Preferences
echo -e "${YELLOW}Testing Get User Preferences API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/settings/preferences | json_pp

# Test Update User Preferences
echo -e "${YELLOW}Testing Update User Preferences API...${NC}"
curl -s -X PUT -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "theme": "dark",
    "notifications_enabled": true,
    "email_notifications": true,
    "dashboard_view": "detailed"
  }' \
  $BASE_URL/settings/preferences | json_pp

# Test Get Organization Settings
echo -e "${YELLOW}Testing Get Organization Settings API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/settings/organization | json_pp

# Test Update Organization Settings
echo -e "${YELLOW}Testing Update Organization Settings API...${NC}"
curl -s -X PUT -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "name": "Test Organization",
    "address": "123 Test Street, Test City",
    "contact_email": "org@example.com",
    "logo_url": "https://example.com/logo.png",
    "invoice_prefix": "INV-",
    "contract_prefix": "CONT-",
    "fiscal_year_start": "01-01"
  }' \
  $BASE_URL/settings/organization | json_pp

# ===== User API Tests =====
echo -e "${BLUE}=== User API Tests ===${NC}"

# Test Get All Users
echo -e "${YELLOW}Testing Get All Users API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/users | json_pp

# Test Create User
echo -e "${YELLOW}Testing Create User API...${NC}"
USER_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "email": "apitestuser@example.com",
    "name": "API Test User",
    "role": "USER"
  }' \
  $BASE_URL/users)
echo $USER_RESPONSE | json_pp

# Extract user ID from response
USER_ID=$(echo $USER_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
if [ -n "$USER_ID" ]; then
  echo -e "${GREEN}Successfully created user with ID $USER_ID${NC}"
else
  echo -e "${RED}Failed to get user ID${NC}"
  # Use a fallback ID for testing
  USER_ID=2
fi

# Test Get User Details
echo -e "${YELLOW}Testing Get User Details API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/users/$USER_ID | json_pp

# Test Update User
echo -e "${YELLOW}Testing Update User API...${NC}"
curl -s -X PUT -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -d '{
    "name": "Updated API Test User",
    "role": "MANAGER"
  }' \
  $BASE_URL/users/$USER_ID | json_pp

# Test Delete User
echo -e "${YELLOW}Testing Delete User API...${NC}"
curl -s -X DELETE -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/users/$USER_ID | json_pp

# Test Get Current User
echo -e "${YELLOW}Testing Get Current User API...${NC}"
curl -s -X GET -H "Authorization: Bearer $AUTH_TOKEN" \
  $BASE_URL/users/me | json_pp

echo -e "${BLUE}=== API Testing Complete ===${NC}"