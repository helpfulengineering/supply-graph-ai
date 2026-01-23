#!/bin/bash
# Complete deployment after build finishes
# This script verifies the image was pushed and deploys to Cloud Run

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-nathan-playground-368310}"
REGION="${GCP_REGION:-us-west1}"
AR_REGISTRY="${AR_REGISTRY:-us-west1-docker.pkg.dev}"
AR_REPOSITORY="${AR_REPOSITORY:-cloud-run-source-deploy}"
SERVICE_NAME="${SERVICE_NAME:-supply-graph-ai}"

IMAGE_LATEST="${AR_REGISTRY}/${PROJECT_ID}/${AR_REPOSITORY}/${SERVICE_NAME}:latest"

echo "=========================================="
echo "Completing Cloud Run Deployment"
echo "=========================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "Image: ${IMAGE_LATEST}"
echo "=========================================="
echo ""

# Step 1: Verify image exists
echo "Step 1: Verifying image exists in Artifact Registry..."
if gcloud artifacts docker images describe ${IMAGE_LATEST} --project=${PROJECT_ID} >/dev/null 2>&1; then
  echo "✅ Image found: ${IMAGE_LATEST}"
else
  echo "❌ ERROR: Image not found in Artifact Registry"
  echo "Available images:"
  gcloud artifacts docker images list ${AR_REGISTRY}/${PROJECT_ID}/${AR_REPOSITORY}/${SERVICE_NAME} --project=${PROJECT_ID} || true
  exit 1
fi

# Step 2: Deploy to Cloud Run
echo ""
echo "Step 2: Deploying to Cloud Run..."
echo "Using image: ${IMAGE_LATEST}"
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_LATEST} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --platform managed

# Step 3: Get service URL
echo ""
echo "Step 3: Getting service URL..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format="value(status.url)")

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo "Service URL: ${SERVICE_URL}"
echo "Image: ${IMAGE_LATEST}"
echo ""
echo "To view logs:"
echo "  gcloud run services logs read ${SERVICE_NAME} --region ${REGION} --limit 50"
echo ""
echo "To view logs from matching_service.py:"
echo "  gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME} AND jsonPayload.module=matching_service\" --limit 50"
echo "=========================================="
