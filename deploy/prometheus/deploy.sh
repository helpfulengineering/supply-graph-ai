#!/bin/bash
# Deploy Prometheus to Cloud Run for scraping supply-graph-ai metrics

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-${PROJECT_ID:-nathan-playground-368310}}"
REGION="${REGION:-us-west1}"
SERVICE_NAME="${PROMETHEUS_SERVICE_NAME:-prometheus-supply-graph-ai}"
TARGET_SERVICE_URL="${TARGET_SERVICE_URL:-supply-graph-ai-1085931013579.us-west1.run.app}"

echo "=========================================="
echo "Deploying Prometheus to Cloud Run"
echo "=========================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service Name: $SERVICE_NAME"
echo "Target Service: $TARGET_SERVICE_URL"
echo ""

# Build and push the Docker image using Cloud Build
echo "Building and pushing Prometheus Docker image..."
IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/prometheus:latest"

# Create a minimal build context with only the Dockerfile and entrypoint script
# Use a temporary directory to avoid uploading the entire repo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_DIR=$(mktemp -d)
cp "${SCRIPT_DIR}/Dockerfile" "${TEMP_DIR}/Dockerfile"
cp "${SCRIPT_DIR}/entrypoint.sh" "${TEMP_DIR}/entrypoint.sh"

# Create cloudbuild config in temp dir
# Use printf to ensure IMAGE_TAG is expanded as shell variable
# Enable BuildKit for --chmod support
cat > "${TEMP_DIR}/cloudbuild.yaml" <<YAML_EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    env:
      - 'DOCKER_BUILDKIT=1'
    args:
      - 'build'
      - '-t'
      - '${IMAGE_TAG}'
      - '.'
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '${IMAGE_TAG}'
images:
  - '${IMAGE_TAG}'
options:
  machineType: 'E2_HIGHCPU_8'
  logging: CLOUD_LOGGING_ONLY
YAML_EOF

# Verify the variable was expanded (for debugging)
echo "Generated cloudbuild.yaml with IMAGE_TAG: ${IMAGE_TAG}"
grep -q "${IMAGE_TAG}" "${TEMP_DIR}/cloudbuild.yaml" || {
  echo "ERROR: IMAGE_TAG variable was not expanded in cloudbuild.yaml"
  exit 1
}

# Verify the generated config file doesn't have unexpanded variables
if grep -q '\${_IMAGE_TAG}' "${TEMP_DIR}/cloudbuild.yaml" 2>/dev/null; then
  echo "ERROR: Found unexpanded _IMAGE_TAG in cloudbuild.yaml"
  cat "${TEMP_DIR}/cloudbuild.yaml"
  rm -rf "${TEMP_DIR}"
  exit 1
fi

echo "Generated cloudbuild.yaml (first 20 lines):"
head -20 "${TEMP_DIR}/cloudbuild.yaml"
echo ""

# Build from the minimal context
# --config path is relative to the source directory (last argument)
cd "${TEMP_DIR}"
gcloud builds submit \
  --config cloudbuild.yaml \
  --project ${PROJECT_ID} \
  .
cd - > /dev/null

# Cleanup
rm -rf "${TEMP_DIR}"

# Deploy to Cloud Run
echo ""
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_TAG} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 1 \
  --set-env-vars="TARGET_SERVICE_URL=${TARGET_SERVICE_URL}" \
  --project ${PROJECT_ID}

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(status.url)')

echo ""
echo "=========================================="
echo "✅ Prometheus deployed successfully!"
echo "=========================================="
echo "Service URL: $SERVICE_URL"
echo ""
echo "Access Prometheus UI:"
echo "  $SERVICE_URL"
echo ""
echo "Check targets:"
echo "  $SERVICE_URL/targets"
echo ""
echo "Query metrics:"
echo "  $SERVICE_URL/graph"
echo ""
echo "Example query:"
echo "  http_requests_total"

