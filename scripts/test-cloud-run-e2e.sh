#!/bin/bash
# Comprehensive End-to-End Testing Script for Cloud Run Service
# Tests all major API endpoints with authentication support

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_URL="${SERVICE_URL:-}"
API_KEY="${API_KEY:-}"
IDENTITY_TOKEN="${IDENTITY_TOKEN:-}"  # For GCP Cloud Run authentication
USE_AUTH="${USE_AUTH:-true}"  # Whether to use authentication

# Validate required parameters
if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}Error: SERVICE_URL environment variable is required${NC}"
    echo "Example: export SERVICE_URL=https://supply-graph-ai-1085931013579.us-west1.run.app"
    exit 1
fi

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0
TEST_RESULTS=()

# Helper function to build auth header
get_auth_header() {
    if [ "$USE_AUTH" = "true" ]; then
        if [ -n "$IDENTITY_TOKEN" ]; then
            echo "Authorization: Bearer ${IDENTITY_TOKEN}"
        elif [ -n "$API_KEY" ]; then
            echo "Authorization: Bearer ${API_KEY}"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Helper function to run a test
run_test() {
    local test_name="$1"
    local method="${2:-GET}"
    local url="$3"
    local expected_status="${4:-200}"
    local description="${5:-}"
    local data="${6:-}"  # JSON data for POST/PUT requests
    local auth_header=$(get_auth_header)
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -e "\n${YELLOW}[TEST $TESTS_TOTAL]${NC} $test_name"
    if [ -n "$description" ]; then
        echo "  Description: $description"
    fi
    echo "  Method: $method"
    echo "  URL: $url"
    
    # Build curl command
    local curl_cmd="curl -s -w \"\n%{http_code}\" -X $method"
    
    if [ -n "$auth_header" ]; then
        curl_cmd="$curl_cmd -H \"$auth_header\""
    fi
    
    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -H \"Content-Type: application/json\" -d '$data'"
    fi
    
    curl_cmd="$curl_cmd \"$url\""
    
    response=$(eval $curl_cmd 2>&1)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $http_code)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        TEST_RESULTS+=("PASS: $test_name")
        
        # Pretty print JSON if response is JSON
        if echo "$body" | jq . >/dev/null 2>&1; then
            echo "  Response (first 10 lines):"
            echo "$body" | jq . | head -10 | sed 's/^/    /'
            if [ $(echo "$body" | jq . | wc -l) -gt 10 ]; then
                echo "    ... (truncated)"
            fi
        else
            echo "  Response: $(echo "$body" | head -3 | sed 's/^/    /')"
        fi
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (Expected HTTP $expected_status, got $http_code)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        TEST_RESULTS+=("FAIL: $test_name (expected $expected_status, got $http_code)")
        echo "  Response:"
        echo "$body" | head -10 | sed 's/^/    /'
        return 1
    fi
}

# Helper function to extract JSON field
extract_json_field() {
    local json="$1"
    local field="$2"
    echo "$json" | jq -r ".$field // empty" 2>/dev/null || echo ""
}

echo "=========================================="
echo "Cloud Run End-to-End Testing"
echo "=========================================="
echo "Service URL: $SERVICE_URL"
echo "Authentication: $([ "$USE_AUTH" = "true" ] && echo "Enabled" || echo "Disabled")"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# ==========================================
# Section 1: Health & System Endpoints
# ==========================================
echo -e "\n${BLUE}=== Section 1: Health & System Endpoints ===${NC}"

run_test \
    "Basic Health Check" \
    "GET" \
    "$SERVICE_URL/health" \
    200 \
    "Should return 200 with status, domains, and version"

run_test \
    "Liveness Probe" \
    "GET" \
    "$SERVICE_URL/health/liveness" \
    200 \
    "Should return 200 indicating service is alive"

run_test \
    "Readiness Probe" \
    "GET" \
    "$SERVICE_URL/health/readiness" \
    200 \
    "Should return 200 when all dependencies are ready"

run_test \
    "API Root" \
    "GET" \
    "$SERVICE_URL/" \
    200 \
    "Should return API information"

run_test \
    "API Version Info" \
    "GET" \
    "$SERVICE_URL/v1" \
    200 \
    "Should return API version information"

# ==========================================
# Section 2: Authentication Tests
# ==========================================
echo -e "\n${BLUE}=== Section 2: Authentication Tests ===${NC}"

# Test without authentication (should fail if auth is required)
if [ "$USE_AUTH" = "true" ]; then
    USE_AUTH_SAVE="$USE_AUTH"
    USE_AUTH="false"
    run_test \
        "Unauthenticated Request (401)" \
        "GET" \
        "$SERVICE_URL/v1/api/okh?page=1&page_size=1" \
        401 \
        "Should return 401 for unauthenticated requests"
    USE_AUTH="$USE_AUTH_SAVE"
    
    # Test with invalid API key
    if [ -n "$API_KEY" ] || [ -n "$IDENTITY_TOKEN" ]; then
        INVALID_KEY="invalid-key-12345"
        API_KEY_SAVE="$API_KEY"
        IDENTITY_TOKEN_SAVE="$IDENTITY_TOKEN"
        API_KEY="$INVALID_KEY"
        IDENTITY_TOKEN=""
        run_test \
            "Invalid API Key (401)" \
            "GET" \
            "$SERVICE_URL/v1/api/okh?page=1&page_size=1" \
            401 \
            "Should return 401 for invalid API key"
        API_KEY="$API_KEY_SAVE"
        IDENTITY_TOKEN="$IDENTITY_TOKEN_SAVE"
    fi
fi

# ==========================================
# Section 3: Utility & Metadata Endpoints
# ==========================================
echo -e "\n${BLUE}=== Section 3: Utility & Metadata Endpoints ===${NC}"

run_test \
    "List Domains" \
    "GET" \
    "$SERVICE_URL/v1/api/utility/domains" \
    200 \
    "Should list available domains"

run_test \
    "Get Contexts (Manufacturing)" \
    "GET" \
    "$SERVICE_URL/v1/api/utility/contexts?domain=manufacturing" \
    200 \
    "Should list validation contexts for manufacturing domain"

run_test \
    "Get OKW Schema" \
    "GET" \
    "$SERVICE_URL/v1/api/okw/schema" \
    200 \
    "Should return OKW JSON schema"

run_test \
    "Get OKH Schema" \
    "GET" \
    "$SERVICE_URL/v1/api/okh/schema" \
    200 \
    "Should return OKH JSON schema"

# ==========================================
# Section 4: Read Operations (List/Search)
# ==========================================
echo -e "\n${BLUE}=== Section 4: Read Operations ===${NC}"

run_test \
    "List OKH Manifests" \
    "GET" \
    "$SERVICE_URL/v1/api/okh?page=1&page_size=10" \
    200 \
    "Should list OKH manifests from storage"

run_test \
    "List OKW Facilities" \
    "GET" \
    "$SERVICE_URL/v1/api/okw/search?page=1&page_size=10" \
    200 \
    "Should list OKW facilities from storage"

run_test \
    "List Supply Trees" \
    "GET" \
    "$SERVICE_URL/v1/api/supply-tree?page=1&page_size=10" \
    200 \
    "Should list supply trees from storage"

run_test \
    "List Match Domains" \
    "GET" \
    "$SERVICE_URL/v1/api/match/domains" \
    200 \
    "Should list available match domains"

# ==========================================
# Section 5: Create Operations
# ==========================================
echo -e "\n${BLUE}=== Section 5: Create Operations ===${NC}"

# Create test OKH manifest
OKH_DATA='{
  "title": "Test IoT Sensor Node",
  "version": "1.0.0",
  "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
  "licensor": "Test User",
  "documentation_language": "en",
  "function": "IoT sensor node for testing",
  "description": "A test OKH manifest for E2E testing",
  "intended_use": "Testing purposes",
  "keywords": ["test", "iot", "sensor"],
  "project_link": "https://example.com/test",
  "manufacturing_processes": ["3D Printing", "PCB Assembly"],
  "tool_list": ["3D Printer", "Soldering Iron"],
  "materials": [{"name": "Arduino Nano", "quantity": 1}]
}'

OKH_RESPONSE=$(run_test \
    "Create OKH Manifest" \
    "POST" \
    "$SERVICE_URL/v1/api/okh/create" \
    201 \
    "Should create a new OKH manifest" \
    "$OKH_DATA" 2>&1)

OKH_ID=$(echo "$OKH_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")

if [ -n "$OKH_ID" ]; then
    echo "  Created OKH ID: $OKH_ID"
    
    # Test retrieving the created OKH
    run_test \
        "Retrieve Created OKH" \
        "GET" \
        "$SERVICE_URL/v1/api/okh/$OKH_ID" \
        200 \
        "Should retrieve the created OKH manifest"
fi

# Create test OKW facility
OKW_DATA='{
  "name": "Test Manufacturing Facility",
  "facility_status": "active",
  "access_type": "public",
  "location": {
    "address": {
      "street": "123 Test St",
      "city": "Test City",
      "country": "USA"
    },
    "coordinates": {"latitude": 37.7749, "longitude": -122.4194}
  },
  "manufacturing_processes": ["3D Printing", "CNC Machining"],
  "equipment": [{"name": "Test 3D Printer", "type": "3D Printer"}],
  "typical_materials": ["PLA", "ABS"]
}'

OKW_RESPONSE=$(run_test \
    "Create OKW Facility" \
    "POST" \
    "$SERVICE_URL/v1/api/okw/create" \
    201 \
    "Should create a new OKW facility" \
    "$OKW_DATA" 2>&1)

OKW_ID=$(echo "$OKW_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")

if [ -n "$OKW_ID" ]; then
    echo "  Created OKW ID: $OKW_ID"
    
    # Test retrieving the created OKW
    run_test \
        "Retrieve Created OKW" \
        "GET" \
        "$SERVICE_URL/v1/api/okw/$OKW_ID" \
        200 \
        "Should retrieve the created OKW facility"
fi

# ==========================================
# Section 6: Match Operations
# ==========================================
echo -e "\n${BLUE}=== Section 6: Match Operations ===${NC}"

if [ -n "$OKH_ID" ]; then
    MATCH_DATA="{\"okh_manifest_id\": \"$OKH_ID\"}"
    run_test \
        "Match OKH to OKW" \
        "POST" \
        "$SERVICE_URL/v1/api/match" \
        200 \
        "Should match OKH manifest to OKW facilities" \
        "$MATCH_DATA"
fi

# ==========================================
# Section 7: Error Handling Tests
# ==========================================
echo -e "\n${BLUE}=== Section 7: Error Handling Tests ===${NC}"

run_test \
    "Invalid Endpoint (404)" \
    "GET" \
    "$SERVICE_URL/v1/api/nonexistent" \
    404 \
    "Should return 404 for non-existent endpoints"

run_test \
    "Invalid Resource ID (404)" \
    "GET" \
    "$SERVICE_URL/v1/api/okh/00000000-0000-0000-0000-000000000000" \
    404 \
    "Should return 404 for non-existent resource"

run_test \
    "Invalid Query Parameters (422)" \
    "GET" \
    "$SERVICE_URL/v1/api/okw/search?page=-1" \
    422 \
    "Should return 422 for invalid query parameters"

# ==========================================
# Section 8: Metrics Endpoints
# ==========================================
echo -e "\n${BLUE}=== Section 8: Metrics Endpoints ===${NC}"

run_test \
    "Metrics (JSON Format)" \
    "GET" \
    "$SERVICE_URL/v1/api/utility/metrics?format=json" \
    200 \
    "Should return metrics in JSON format"

run_test \
    "Metrics (Prometheus Format)" \
    "GET" \
    "$SERVICE_URL/v1/api/utility/metrics?format=prometheus" \
    200 \
    "Should return metrics in Prometheus text format"

# ==========================================
# Cleanup (if IDs were created)
# ==========================================
if [ -n "$OKH_ID" ] || [ -n "$OKW_ID" ]; then
    echo -e "\n${BLUE}=== Cleanup ===${NC}"
    
    if [ -n "$OKH_ID" ]; then
        run_test \
            "Delete Created OKH" \
            "DELETE" \
            "$SERVICE_URL/v1/api/okh/$OKH_ID" \
            200 \
            "Should delete the created OKH manifest"
    fi
    
    if [ -n "$OKW_ID" ]; then
        run_test \
            "Delete Created OKW" \
            "DELETE" \
            "$SERVICE_URL/v1/api/okw/$OKW_ID" \
            200 \
            "Should delete the created OKW facility"
    fi
fi

# ==========================================
# Summary
# ==========================================
echo -e "\n=========================================="
echo "Test Summary"
echo "=========================================="
echo "Total Tests: $TESTS_TOTAL"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo ""
    echo "Failed Tests:"
    for result in "${TEST_RESULTS[@]}"; do
        if [[ $result == FAIL:* ]]; then
            echo "  - $result"
        fi
    done
else
    echo -e "${GREEN}Failed: $TESTS_FAILED${NC}"
fi

echo ""
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi

