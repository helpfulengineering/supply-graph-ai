#!/bin/bash
# Get identity token for user account to access Cloud Run

SERVICE_URL="${1:-https://supply-graph-ai-1085931013579.us-west1.run.app}"
SERVICE_ACCOUNT="${2:-supply-graph-ai@nathan-playground-368310.iam.gserviceaccount.com}"

echo "Getting identity token for Cloud Run service..."
echo "Service URL: $SERVICE_URL"
echo "Service Account: $SERVICE_ACCOUNT"
echo ""

# Method 1: Try impersonating the service account (if you have permission)
echo "Method 1: Impersonating service account..."
if TOKEN=$(gcloud auth print-identity-token --impersonate-service-account="$SERVICE_ACCOUNT" --audiences="$SERVICE_URL" 2>/dev/null); then
    echo "$TOKEN"
    echo ""
    echo "✓ Success! Token generated using service account impersonation."
    exit 0
fi

# Method 2: Try without impersonation (user account token)
echo "Method 2: Using user account token (may not work)..."
if TOKEN=$(gcloud auth print-identity-token 2>/dev/null); then
    echo "$TOKEN"
    echo ""
    echo "⚠ Token generated but may not work for Cloud Run."
    echo ""
    echo "If you get 401 errors, try:"
    echo "  1. Grant yourself permission to impersonate the service account:"
    echo "     gcloud iam service-accounts add-iam-policy-binding $SERVICE_ACCOUNT \\"
    echo "       --member='user:$(gcloud config get-value account)' \\"
    echo "       --role='roles/iam.serviceAccountTokenCreator'"
    echo ""
    echo "  2. Then use service account impersonation:"
    echo "     gcloud auth print-identity-token --impersonate-service-account=$SERVICE_ACCOUNT --audiences=$SERVICE_URL"
    exit 0
fi

echo "❌ Failed to get identity token"
exit 1
