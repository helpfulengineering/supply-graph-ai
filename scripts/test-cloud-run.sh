#!/bin/bash
# Cloud Run End-to-End Testing Script
# Tests the deployed supply-graph-ai service on GCP Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SERVICE_URL="${SERVICE_URL:-}"
if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}Error: SERVICE_URL environment variable is required${NC}"
    echo "Example: export SERVICE_URL=https://supply-graph-ai-1085931013579.us-west1.run.app"
    exit 1
fi

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Helper function to run a test
run_test() {
    local test_name="$1"
    local url="$2"
    local expected_status="${3:-200}"
    local description="${4:-}"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -e "\n${YELLOW}[TEST $TESTS_TOTAL]${NC} $test_name"
    if [ -n "$description" ]; then
        echo "  Description: $description"
    fi
    echo "  URL: $url"
    
    response=$(curl -s -w "\n%{http_code}" "$url" 2>&1)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $http_code)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        
        # Pretty print JSON if response is JSON
        if echo "$body" | jq . >/dev/null 2>&1; then
            echo "  Response:"
            echo "$body" | jq . | head -20 | sed 's/^/    /'
            if [ $(echo "$body" | jq . | wc -l) -gt 20 ]; then
                echo "    ... (truncated)"
            fi
        else
            echo "  Response: $body" | head -5 | sed 's/^/    /'
        fi
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (Expected HTTP $expected_status, got $http_code)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo "  Response: $body" | head -10 | sed 's/^/    /'
        return 1
    fi
}

# Helper function to check JSON response contains key
check_json_key() {
    local json="$1"
    local key="$2"
    if echo "$json" | jq -e ".$key" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

echo "=========================================="
echo "Cloud Run End-to-End Testing"
echo "=========================================="
echo "Service URL: $SERVICE_URL"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# ==========================================
# Section 1: Health & Readiness Checks
# ==========================================
echo -e "\n${YELLOW}=== Section 1: Health & Readiness Checks ===${NC}"

run_test \
    "Basic Health Check" \
    "$SERVICE_URL/health" \
    200 \
    "Should return 200 with status, domains, and version"

run_test \
    "Liveness Probe" \
    "$SERVICE_URL/health/liveness" \
    200 \
    "Should return 200 indicating service is alive"

run_test \
    "Readiness Probe" \
    "$SERVICE_URL/health/readiness" \
    200 \
    "Should return 200 when all dependencies (storage, auth, domains) are ready"

# ==========================================
# Section 2: Metrics Endpoints
# ==========================================
echo -e "\n${YELLOW}=== Section 2: Metrics Endpoints ===${NC}"

run_test \
    "Metrics (JSON Format)" \
    "$SERVICE_URL/v1/api/utility/metrics?format=json" \
    200 \
    "Should return metrics in JSON format"

run_test \
    "Metrics (Prometheus Format)" \
    "$SERVICE_URL/v1/api/utility/metrics?format=prometheus" \
    200 \
    "Should return metrics in Prometheus text format"

# ==========================================
# Section 3: Storage Access Tests
# ==========================================
echo -e "\n${YELLOW}=== Section 3: Storage Access Tests ===${NC}"

run_test \
    "List Domains" \
    "$SERVICE_URL/v1/api/utility/domains" \
    200 \
    "Should list available domains (tests basic API connectivity)"

run_test \
    "List OKW Facilities (Storage Access)" \
    "$SERVICE_URL/v1/api/okw/search?page=1&page_size=10" \
    200 \
    "Should list OKW facilities from cloud storage (tests GCS read access)"

run_test \
    "List OKH Manifests (Storage Access)" \
    "$SERVICE_URL/v1/api/okh?page=1&page_size=10" \
    200 \
    "Should list OKH manifests from cloud storage (tests GCS read access)"

run_test \
    "List Supply Trees (Storage Access)" \
    "$SERVICE_URL/v1/api/supply-tree?page=1&page_size=10" \
    200 \
    "Should list supply trees from cloud storage (tests GCS read access)"

# ==========================================
# Section 4: API Functionality Tests
# ==========================================
echo -e "\n${YELLOW}=== Section 4: API Functionality Tests ===${NC}"

run_test \
    "Get OKW Schema" \
    "$SERVICE_URL/v1/api/okw/schema" \
    200 \
    "Should return OKW JSON schema"

run_test \
    "List Contexts" \
    "$SERVICE_URL/v1/api/utility/contexts?domain=manufacturing" \
    200 \
    "Should list validation contexts for manufacturing domain"

# ==========================================
# Section 5: Error Handling Tests
# ==========================================
echo -e "\n${YELLOW}=== Section 5: Error Handling Tests ===${NC}"

run_test \
    "Invalid Endpoint (404)" \
    "$SERVICE_URL/v1/api/nonexistent" \
    404 \
    "Should return 404 for non-existent endpoints"

run_test \
    "Invalid Query Parameters" \
    "$SERVICE_URL/v1/api/okw/search?page=-1" \
    422 \
    "Should return 422 for invalid query parameters"

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
else
    echo -e "${GREEN}Failed: $TESTS_FAILED${NC}"
fi

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Some tests failed${NC}"
    exit 1
fi

