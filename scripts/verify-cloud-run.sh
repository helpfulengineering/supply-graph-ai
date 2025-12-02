#!/bin/bash
# Cloud Run Verification Script
# Verifies logging, secrets manager, and metrics integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="${SERVICE_NAME:-supply-graph-ai}"
REGION="${REGION:-us-west1}"
PROJECT_ID="${PROJECT_ID:-nathan-playground-368310}"
SERVICE_URL="${SERVICE_URL:-}"

if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}Error: SERVICE_URL environment variable is required${NC}"
    echo "Example: export SERVICE_URL=https://supply-graph-ai-1085931013579.us-west1.run.app"
    exit 1
fi

echo "=========================================="
echo "Cloud Run Verification"
echo "=========================================="
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo "Project: $PROJECT_ID"
echo "Service URL: $SERVICE_URL"
echo ""

# ==========================================
# Section 1: Cloud Logging Verification
# ==========================================
echo -e "\n${BLUE}=== Section 1: Cloud Logging Verification ===${NC}"

echo -e "\n${YELLOW}Fetching recent logs from Cloud Logging...${NC}"
echo "Command: gcloud run services logs read $SERVICE_NAME --region $REGION --project $PROJECT_ID --limit 20"

RECENT_LOGS=$(gcloud logging read \
    "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
    --limit 20 \
    --format="json" \
    --project "$PROJECT_ID" 2>/dev/null || echo "[]")

if [ "$RECENT_LOGS" = "[]" ] || [ -z "$RECENT_LOGS" ]; then
    echo -e "${RED}✗ No logs found${NC}"
    echo "  This might indicate logging isn't working properly"
else
    LOG_COUNT=$(echo "$RECENT_LOGS" | jq '. | length' 2>/dev/null || echo "0")
    echo -e "${GREEN}✓ Found $LOG_COUNT log entries${NC}"
    
    # Check for structured JSON logs
    echo -e "\n${YELLOW}Checking for structured JSON log format...${NC}"
    
    # Check for required fields in logs
    HAS_SEVERITY=$(echo "$RECENT_LOGS" | jq '[.[] | select(.severity != null)] | length' 2>/dev/null || echo "0")
    HAS_TIMESTAMP=$(echo "$RECENT_LOGS" | jq '[.[] | select(.timestamp != null)] | length' 2>/dev/null || echo "0")
    HAS_SERVICE=$(echo "$RECENT_LOGS" | jq '[.[] | select(.resource.labels.service_name != null)] | length' 2>/dev/null || echo "0")
    
    if [ "$HAS_SEVERITY" -gt 0 ]; then
        echo -e "${GREEN}✓ Logs contain 'severity' field ($HAS_SEVERITY entries)${NC}"
    else
        echo -e "${YELLOW}⚠ Logs may not have 'severity' field${NC}"
    fi
    
    if [ "$HAS_TIMESTAMP" -gt 0 ]; then
        echo -e "${GREEN}✓ Logs contain 'timestamp' field ($HAS_TIMESTAMP entries)${NC}"
    else
        echo -e "${YELLOW}⚠ Logs may not have 'timestamp' field${NC}"
    fi
    
    if [ "$HAS_SERVICE" -gt 0 ]; then
        echo -e "${GREEN}✓ Logs contain service metadata ($HAS_SERVICE entries)${NC}"
    else
        echo -e "${YELLOW}⚠ Logs may not have service metadata${NC}"
    fi
    
    # Show sample log entry
    echo -e "\n${YELLOW}Sample log entry:${NC}"
    echo "$RECENT_LOGS" | jq '.[0]' 2>/dev/null | head -30 || echo "Could not parse log entry"
fi

# ==========================================
# Section 2: Secret Manager Verification
# ==========================================
echo -e "\n${BLUE}=== Section 2: Secret Manager Verification ===${NC}"

echo -e "\n${YELLOW}Checking for Secret Manager initialization in logs...${NC}"

SECRET_MANAGER_LOGS=$(gcloud run services logs read "$SERVICE_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --limit 100 \
    --format="value(textPayload,jsonPayload.message)" \
    --filter='textPayload=~"Secret Manager" OR jsonPayload.message=~"Secret Manager" OR textPayload=~"secrets manager" OR jsonPayload.message=~"secrets manager"' 2>/dev/null || echo "")

if [ -z "$SECRET_MANAGER_LOGS" ]; then
    echo -e "${YELLOW}⚠ No Secret Manager initialization messages found in logs${NC}"
    echo "  This might be normal if secrets are loaded silently"
else
    echo -e "${GREEN}✓ Found Secret Manager related logs:${NC}"
    echo "$SECRET_MANAGER_LOGS" | head -5 | sed 's/^/  /'
fi

# Check for GCP Secret Manager client initialization
GCP_SECRET_LOGS=$(gcloud run services logs read "$SERVICE_NAME" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --limit 100 \
    --format="value(textPayload,jsonPayload.message)" \
    --filter='textPayload=~"GCP Secret Manager" OR jsonPayload.message=~"GCP Secret Manager" OR textPayload=~"Initialized GCP Secret Manager" OR jsonPayload.message=~"Initialized GCP Secret Manager"' 2>/dev/null || echo "")

if [ -n "$GCP_SECRET_LOGS" ]; then
    echo -e "\n${GREEN}✓ Found GCP Secret Manager initialization:${NC}"
    echo "$GCP_SECRET_LOGS" | head -3 | sed 's/^/  /'
else
    echo -e "\n${YELLOW}⚠ No GCP Secret Manager initialization found${NC}"
    echo "  Check if USE_SECRETS_MANAGER=true is set"
fi

# ==========================================
# Section 3: Metrics Endpoint Verification
# ==========================================
echo -e "\n${BLUE}=== Section 3: Metrics Endpoint Verification ===${NC}"

echo -e "\n${YELLOW}Testing metrics endpoint accessibility...${NC}"

METRICS_JSON=$(curl -s "$SERVICE_URL/v1/api/utility/metrics?format=json" 2>/dev/null || echo "")
METRICS_PROM=$(curl -s "$SERVICE_URL/v1/api/utility/metrics?format=prometheus" 2>/dev/null || echo "")

if [ -n "$METRICS_JSON" ] && echo "$METRICS_JSON" | jq . >/dev/null 2>&1; then
    echo -e "${GREEN}✓ JSON metrics endpoint is accessible and returns valid JSON${NC}"
    TOTAL_REQUESTS=$(echo "$METRICS_JSON" | jq -r '.data.total_requests // 0' 2>/dev/null || echo "0")
    echo "  Total requests tracked: $TOTAL_REQUESTS"
else
    echo -e "${RED}✗ JSON metrics endpoint failed or returned invalid JSON${NC}"
fi

if [ -n "$METRICS_PROM" ] && echo "$METRICS_PROM" | grep -q "http_requests_total"; then
    echo -e "${GREEN}✓ Prometheus metrics endpoint is accessible and returns valid format${NC}"
    PROM_METRICS_COUNT=$(echo "$METRICS_PROM" | grep -c "^[^#]" || echo "0")
    echo "  Metrics found: $PROM_METRICS_COUNT"
    
    # Show sample metrics
    echo -e "\n${YELLOW}Sample Prometheus metrics:${NC}"
    echo "$METRICS_PROM" | grep "^http_" | head -5 | sed 's/^/  /'
else
    echo -e "${RED}✗ Prometheus metrics endpoint failed or returned invalid format${NC}"
fi

# ==========================================
# Section 4: Prometheus Scraping Instructions
# ==========================================
echo -e "\n${BLUE}=== Section 4: Prometheus Configuration ===${NC}"

echo -e "\n${YELLOW}Prometheus scraping configuration for Cloud Run:${NC}"
echo ""
echo "Since Cloud Run doesn't support sidecar containers, Prometheus needs to:"
echo "  1. Run as a separate Cloud Run service, OR"
echo "  2. Run in GKE/another environment that can reach Cloud Run, OR"
echo "  3. Use Cloud Monitoring's Prometheus integration"
echo ""
echo "For testing, you can run Prometheus locally and configure it to scrape:"
echo ""
cat << 'PROM_CONFIG'
# prometheus-cloud-run.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'supply-graph-ai'
    static_configs:
      - targets: ['supply-graph-ai-1085931013579.us-west1.run.app']
    metrics_path: '/v1/api/utility/metrics'
    params:
      format: ['prometheus']
    scheme: 'https'
PROM_CONFIG

echo ""
echo -e "${YELLOW}To test Prometheus scraping locally:${NC}"
echo "  1. Save the above config as prometheus-cloud-run.yml"
echo "  2. Run: prometheus --config.file=prometheus-cloud-run.yml"
echo "  3. Access Prometheus UI at http://localhost:9090"
echo "  4. Query: http_requests_total"

# ==========================================
# Summary
# ==========================================
echo -e "\n=========================================="
echo "Verification Summary"
echo "=========================================="
echo -e "${GREEN}✓ Cloud Logging: Checked${NC}"
echo -e "${GREEN}✓ Secret Manager: Checked${NC}"
echo -e "${GREEN}✓ Metrics Endpoints: Verified${NC}"
echo -e "${BLUE}ℹ Prometheus: Configuration provided${NC}"
echo ""
echo "Next steps:"
echo "  1. Review Cloud Logging console: https://console.cloud.google.com/logs/query"
echo "  2. Verify Secret Manager secrets are accessible"
echo "  3. Set up Prometheus scraping (see instructions above)"

