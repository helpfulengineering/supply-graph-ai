#!/bin/bash
# Alternative test script using curl with gcloud auth

SERVICE_URL="https://supply-graph-ai-1085931013579.us-west1.run.app"

echo "Testing Cloud Run service with curl..."
echo "Service URL: $SERVICE_URL"
echo ""

# Get token
echo "Getting identity token..."
TOKEN=$(gcloud auth print-identity-token 2>/dev/null)
if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get token"
    exit 1
fi

echo "✓ Token obtained (length: ${#TOKEN} characters)"
echo ""

# Test health endpoint
echo "Testing /health endpoint..."
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "$SERVICE_URL/health" | head -30

echo ""
echo "---"
echo ""

# Test OKH list endpoint
echo "Testing /v1/api/okh endpoint..."
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" \
  "$SERVICE_URL/v1/api/okh?page=1&page_size=5" | head -30
