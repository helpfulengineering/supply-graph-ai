#!/bin/bash
# Helper script to check Cloud Run logs for errors

SERVICE_NAME="${SERVICE_NAME:-supply-graph-ai}"
PROJECT_ID="${PROJECT_ID:-nathan-playground-368310}"

echo "=========================================="
echo "Cloud Run Logs - Recent Errors"
echo "=========================================="
echo ""

echo "1. Recent ERROR level logs:"
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME} AND severity>=ERROR" \
  --limit 20 \
  --format json \
  --project="${PROJECT_ID}" | jq -r '.[] | "\(.timestamp) [\(.severity)] \(.textPayload // .jsonPayload.message // "No message")"'

echo ""
echo "=========================================="
echo "2. Recent logs with 'Error' or 'Exception' in text:"
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME} AND (textPayload=~\"Error\" OR textPayload=~\"Exception\" OR jsonPayload.message=~\"Error\" OR jsonPayload.message=~\"Exception\")" \
  --limit 20 \
  --format json \
  --project="${PROJECT_ID}" | jq -r '.[] | "\(.timestamp) [\(.severity)] \(.textPayload // .jsonPayload.message // .jsonPayload.error // "No message")"'

echo ""
echo "=========================================="
echo "3. Recent 500 errors:"
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME} AND jsonPayload.status_code=500" \
  --limit 20 \
  --format json \
  --project="${PROJECT_ID}" | jq -r '.[] | "\(.timestamp) \(.jsonPayload.message // .textPayload // "No message")"'

echo ""
echo "=========================================="
echo "4. Full traceback for recent errors:"
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME} AND severity>=ERROR" \
  --limit 5 \
  --format json \
  --project="${PROJECT_ID}" | jq -r '.[] | select(.textPayload != null) | "\(.timestamp)\n\(.textPayload)\n---"'

