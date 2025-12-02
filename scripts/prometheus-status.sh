#!/bin/bash
# Quick script to check Prometheus status and targets

set -e

PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"

echo "=========================================="
echo "Prometheus Status Check"
echo "=========================================="
echo "Prometheus URL: $PROMETHEUS_URL"
echo ""

# Check if Prometheus is running
if ! curl -s "$PROMETHEUS_URL/-/healthy" > /dev/null 2>&1; then
    echo "❌ Prometheus is not accessible at $PROMETHEUS_URL"
    echo "   Make sure Prometheus is running: docker ps | grep prometheus"
    exit 1
fi

echo "✅ Prometheus is running"
echo ""

# Check targets
echo "📊 Target Status:"
echo ""
TARGETS=$(curl -s "$PROMETHEUS_URL/api/v1/targets")

echo "$TARGETS" | jq -r '.data.activeTargets[] | 
  "Job: \(.labels.job // "unknown")
  Health: \(.health // "unknown")
  Last Scrape: \(.lastScrape // "never")
  Last Error: \(.lastError // "none")
  ---"'

echo ""
echo "🔍 Quick Queries:"
echo ""
echo "Total Requests:"
curl -s "$PROMETHEUS_URL/api/v1/query?query=http_requests_total" | jq -r '.data.result[] | "  \(.metric.path // .metric.__name__): \(.value[1])"'

echo ""
echo "🌐 Access Prometheus UI:"
echo "   $PROMETHEUS_URL"
echo "   Targets: $PROMETHEUS_URL/targets"
echo "   Graph: $PROMETHEUS_URL/graph"

