#!/bin/bash
# Build, push, and deploy to Cloud Run
# This script rebuilds the Docker image, pushes it to Artifact Registry, and updates the Cloud Run service

set -e

# Configuration (matching CI/CD workflow)
PROJECT_ID="${GCP_PROJECT_ID:-nathan-playground-368310}"
REGION="${GCP_REGION:-us-west1}"
AR_REGISTRY="${AR_REGISTRY:-us-west1-docker.pkg.dev}"
AR_REPOSITORY="${AR_REPOSITORY:-cloud-run-source-deploy}"
SERVICE_NAME="${SERVICE_NAME:-supply-graph-ai}"

# Image tags
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_NAME="${AR_REGISTRY}/${PROJECT_ID}/${AR_REPOSITORY}/${SERVICE_NAME}"
IMAGE_TAG="${IMAGE_NAME}:${TIMESTAMP}"
IMAGE_LATEST="${IMAGE_NAME}:latest"

echo "=========================================="
echo "Building and Deploying to Cloud Run"
echo "=========================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "Image: ${IMAGE_TAG}"
echo "=========================================="
echo ""

# Step 1: Authenticate Docker for Artifact Registry
echo "Step 1: Configuring Docker for Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Step 2: Build and push using Cloud Build (recommended for Cloud Run)
echo ""
echo "Step 2: Building Docker image with Cloud Build..."
echo "This will build and push the image to Artifact Registry..."
gcloud builds submit --tag ${IMAGE_TAG} --tag ${IMAGE_LATEST} \
  --project=${PROJECT_ID} \
  --region=${REGION}

# Step 3: Verify image exists
echo ""
echo "Step 3: Verifying image was pushed..."
gcloud artifacts docker images describe ${IMAGE_LATEST} || {
  echo "ERROR: Image not found in Artifact Registry"
  exit 1
}

# Step 4: Deploy to Cloud Run
echo ""
echo "Step 4: Deploying to Cloud Run..."
echo "Using image: ${IMAGE_LATEST}"
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_LATEST} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --platform managed

# Step 5: Get service URL
echo ""
echo "Step 5: Getting service URL..."
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
