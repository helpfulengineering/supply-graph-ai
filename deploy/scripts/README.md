# Deployment Scripts

This directory contains scripts for testing and using the deployment system.

## Test Scripts

### `test_gcp_deployer.py`

Test script for the GCP Cloud Run deployer. Allows testing the deployer locally before integrating into CI/CD.

**Usage:**

```bash
# Basic test (dry run - no actual deployment)
python deploy/scripts/test_gcp_deployer.py

# Test with specific project and region
python deploy/scripts/test_gcp_deployer.py \
  --project-id your-project-id \
  --region us-west1 \
  --service-name supply-graph-ai

# Test with actual gcloud commands (requires authentication)
python deploy/scripts/test_gcp_deployer.py --no-dry-run
```

**Environment Variables:**

- `GCP_PROJECT_ID` - GCP project ID (default: test-project-123)
- `GCP_REGION` - GCP region (default: us-west1)
- `AR_REGISTRY` - Artifact Registry registry (default: us-west1-docker.pkg.dev)
- `AR_REPOSITORY` - Artifact Registry repository (default: cloud-run-source-deploy)

**What it tests:**

1. Configuration creation
2. Deployer instantiation
3. Secret handling logic
4. Environment variables building
5. Service status checking (if not dry run)
6. Deployment command building

## Manual Deployment Script

### `deploy_gcp.py`

Script to manually deploy the service to GCP Cloud Run using the deployer.

**Usage:**

```bash
# Basic deployment
python deploy/scripts/deploy_gcp.py \
  --project-id your-project-id \
  --image us-west1-docker.pkg.dev/your-project/repo/image:latest

# Full deployment with all options
python deploy/scripts/deploy_gcp.py \
  --project-id your-project-id \
  --region us-west1 \
  --service-name supply-graph-ai \
  --image us-west1-docker.pkg.dev/your-project/repo/image:latest \
  --storage-bucket supply-graph-ai-storage \
  --memory 4Gi \
  --cpu 2 \
  --timeout 300 \
  --min-instances 1 \
  --max-instances 100

# Allow unauthenticated access (not recommended for production)
python deploy/scripts/deploy_gcp.py \
  --project-id your-project-id \
  --image us-west1-docker.pkg.dev/your-project/repo/image:latest \
  --allow-unauthenticated
```

**Environment Variables:**

- `GCP_PROJECT_ID` - GCP project ID (can be used instead of --project-id)
- `GCP_REGION` - GCP region (default: us-west1)
- `GCP_STORAGE_BUCKET` - GCS storage bucket name (default: supply-graph-ai-storage)

**Prerequisites:**

1. `gcloud` CLI installed and authenticated: `gcloud auth login`
2. Application Default Credentials set up: `gcloud auth application-default login`
3. Required IAM permissions for the authenticated account
4. Docker image built and pushed to Artifact Registry

**What it does:**

1. Creates GCP deployment configuration
2. Checks for secrets in Secret Manager
3. Generates secure values for missing secrets
4. Deploys service to Cloud Run
5. Returns the service URL

