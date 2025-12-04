#!/bin/bash
# Helper script to get a valid identity token for Cloud Run

SERVICE_URL="${1:-https://supply-graph-ai-1085931013579.us-west1.run.app}"

echo "Getting identity token for Cloud Run service..."
echo "Service URL: $SERVICE_URL"
echo ""

# Try with audience first (for service accounts)
echo "Attempting to get token with audience..."
if gcloud auth print-identity-token --audiences="$SERVICE_URL" 2>/dev/null; then
    echo ""
    echo "✓ Success! Token generated with correct audience."
    exit 0
fi

# Try without audience (for user accounts - may not work)
echo "Attempting to get token without audience..."
if TOKEN=$(gcloud auth print-identity-token 2>/dev/null); then
    echo "$TOKEN"
    echo ""
    echo "⚠ Token generated but may not work for Cloud Run."
    echo "If you get 401 errors, you may need to:"
    echo "  1. Grant yourself the invoker role:"
    echo "     gcloud run services add-iam-policy-binding supply-graph-ai \\"
    echo "       --member='user:$(gcloud config get-value account)' \\"
    echo "       --role='roles/run.invoker' \\"
    echo "       --region=us-west1"
    echo ""
    echo "  2. Or use a service account:"
    echo "     gcloud auth activate-service-account SERVICE_ACCOUNT_EMAIL --key-file=KEY_FILE"
    exit 0
fi

echo "❌ Failed to get identity token"
echo ""
echo "Make sure you're authenticated:"
echo "  gcloud auth login"
echo "  gcloud auth application-default login"
exit 1
