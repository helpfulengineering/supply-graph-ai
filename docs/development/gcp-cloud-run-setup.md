# GCP Cloud Run Setup Guide

This guide covers the complete setup process for deploying the Supply Graph AI application to Google Cloud Run with Google Cloud Storage.

## Overview

The setup process involves several steps that must be completed in a specific order to avoid dependency issues. This document outlines the correct sequence and explains the bootstrapping requirements.

## Table of Contents

1. [Quick Reference Checklist](#quick-reference-checklist)
2. [Prerequisites](#prerequisites)
3. [Setup Order and Dependencies](#setup-order-and-dependencies)
4. [Manual Setup Steps](#manual-setup-steps)
5. [Service Account Configuration](#service-account-configuration)
6. [Storage Setup](#storage-setup)
7. [Secrets Manager Setup](#secrets-manager-setup)
8. [Application Configuration](#application-configuration)
9. [Verification](#verification)
10. [Troubleshooting](#troubleshooting)

## Quick Reference Checklist

Use this checklist to quickly verify all setup steps are complete. See detailed instructions in the sections below.

### Phase 1: Infrastructure Setup

- [ ] **GCP Project Created**
  - [ ] Project created with billing enabled
  ```bash
  # Set your project ID
  export PROJECT_ID="your-project-id"
  export REGION="us-central1"
  export BUCKET_NAME="supply-graph-ai-storage"
  
  # Set the project
  gcloud config set project $PROJECT_ID
  ```
  
  - [ ] Required APIs enabled (Cloud Run, Secret Manager, Storage)
  ```bash
  gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    storage-component.googleapis.com \
    storage-api.googleapis.com
  ```

- [ ] **Create Service Account**
  ```bash
  export SA_EMAIL="supply-graph-ai@${PROJECT_ID}.iam.gserviceaccount.com"
  
  gcloud iam service-accounts create supply-graph-ai \
    --display-name="Supply Graph AI Service Account" \
    --description="Service account for Supply Graph AI Cloud Run service"
  ```

- [ ] **IAM Roles Granted**
  - [ ] `roles/secretmanager.secretAccessor` (for Secret Manager access)
  ```bash
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"
  ```

- [ ] **Storage Bucket Created**
  ```bash
  gcloud storage buckets create gs://${BUCKET_NAME} \
    --location=${REGION} \
    --uniform-bucket-level-access
  
  # Verify bucket exists
  gcloud storage buckets describe gs://${BUCKET_NAME}
  ```

- [ ] **Storage Bucket IAM Permissions Granted** (after bucket creation)
  - [ ] `roles/storage.objectAdmin` (for GCS object operations)
  - [ ] `roles/storage.legacyBucketReader` (for bucket metadata access, needed for `bucket.exists()` checks)
  ```bash
  # Grant permissions at bucket level (more secure than project-level)
  gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectAdmin"
  
  gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.legacyBucketReader"
  ```
  
  **Note**: Bucket-level permissions are preferred over project-level for security. The `roles/storage.legacyBucketReader` role is required for the application to check if the bucket exists during startup.

### Phase 2: Secrets and Configuration

- [ ] **Secrets Stored in Secret Manager**
  - [ ] `gcp-project-id` (if not using env var)
  ```bash
  echo -n "$PROJECT_ID" | gcloud secrets create gcp-project-id \
    --data-file=- \
    --replication-policy="automatic"
  ```
  
  - [ ] `gcp-storage-bucket` (if not using env var)
  ```bash
  echo -n "$BUCKET_NAME" | gcloud secrets create gcp-storage-bucket \
    --data-file=- \
    --replication-policy="automatic"
  ```
  
  - [ ] API keys (OpenAI, Anthropic, etc.)
  ```bash
  # Example: Anthropic API key
  echo -n "your-api-key" | gcloud secrets create anthropic-api-key \
    --data-file=- \
    --replication-policy="automatic"
  ```

- [ ] **Service Account Access Granted to Secrets**
  ```bash
  # Grant access to each secret
  gcloud secrets add-iam-policy-binding gcp-project-id \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"
  
  gcloud secrets add-iam-policy-binding gcp-storage-bucket \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"
  
  gcloud secrets add-iam-policy-binding anthropic-api-key \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

  gcloud secrets add-iam-policy-binding azure_storage_key \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"
  ```

### Phase 3: Storage Initialization (Optional)

- [ ] **Directory Structure** (auto-created on first startup, or pre-created via script)
  ```bash
  # Optional: Pre-create using standalone script
  # Requires: conda activate supply-graph-ai
  # Requires: gcloud auth application-default login (for local credentials)
  python scripts/setup_storage.py \
    --provider gcs \
    --bucket ${BUCKET_NAME} \
    --region ${REGION} \
    --project-id ${PROJECT_ID}
  
  # Or with explicit credentials
  python scripts/setup_storage.py \
    --provider gcs \
    --bucket ${BUCKET_NAME} \
    --region ${REGION} \
    --credentials-json /path/to/credentials.json \
    --project-id ${PROJECT_ID}
  ```

- [ ] **Synthetic Data** (optional, can be done after deployment)
  ```bash
  # Requires: conda activate supply-graph-ai
  # Requires: Application codebase and dependencies installed
  # Requires: gcloud auth application-default login (for local credentials)
  # Note: Does NOT require the API server to be running
  ome storage populate \
    --provider gcs \
    --bucket ${BUCKET_NAME} \
    --region ${REGION} \
    --project-id ${PROJECT_ID}
  
  # Or with explicit credentials
  ome storage populate \
    --provider gcs \
    --bucket ${BUCKET_NAME} \
    --region ${REGION} \
    --credentials-json /path/to/credentials.json \
    --project-id ${PROJECT_ID}
  ```
  
  **What this command does:**
  - Loads OKH and OKW JSON files from `synth/synthetic-data/` directory
  - Stores them in the configured storage using the organized directory structure
  - Uses the application's `StorageService` and `StorageOrganizer` classes directly
  - Does NOT require the API server to be running (uses storage libraries only)

### Phase 4: Application Deployment

- [ ] **Artifact Registry Repository Created** (if not exists)
  ```bash
  # Check if repository exists
  gcloud artifacts repositories describe cloud-run-source-deploy \
    --location=${REGION} --project=${PROJECT_ID} || \
  gcloud artifacts repositories create cloud-run-source-deploy \
    --repository-format=docker \
    --location=${REGION} \
    --description="Docker repository for Cloud Run deployments" \
    --project=${PROJECT_ID}
  ```

- [ ] **Container Image Built and Pushed to Artifact Registry**
  ```bash
  # Build and push to Artifact Registry (not deprecated Container Registry)
  TIMESTAMP=$(date +%Y%m%d-%H%M%S)
  IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/supply-graph-ai:${TIMESTAMP}"
  gcloud builds submit --tag ${IMAGE_TAG} --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/supply-graph-ai:latest
  ```

- [ ] **Deployed to Cloud Run**
  ```bash
  # Deploy using the Artifact Registry image
  gcloud run deploy supply-graph-ai \
    --image ${IMAGE_TAG} \
    --service-account ${SA_EMAIL} \
    --region ${REGION} \
    --set-env-vars="STORAGE_PROVIDER=gcs,GCP_STORAGE_BUCKET=${BUCKET_NAME},GCP_PROJECT_ID=${PROJECT_ID},USE_SECRETS_MANAGER=true,SECRETS_PROVIDER=gcp" \
    --allow-unauthenticated
  # Or use --no-allow-unauthenticated for authenticated access
  ```
  
  Configuration details:
  - Service account: `--service-account ${SA_EMAIL}`
  - Environment variables:
    - `STORAGE_PROVIDER=gcs`
    - `GCP_STORAGE_BUCKET=${BUCKET_NAME}`
    - `GCP_PROJECT_ID=${PROJECT_ID}`
    - `USE_SECRETS_MANAGER=true`
    - `SECRETS_PROVIDER=gcp`

### Phase 5: Verification

- [ ] **Service Status Checked**
  ```bash
  gcloud run services describe supply-graph-ai --region ${REGION}
  ```

- [ ] **Get Service URL**
  ```bash
  SERVICE_URL=$(gcloud run services describe supply-graph-ai \
    --region ${REGION} \
    --format 'value(status.url)')
  echo "Service URL: $SERVICE_URL"
  ```

- [ ] **Health Endpoints Tested**
  ```bash
  # Basic health check
  curl ${SERVICE_URL}/health
  
  # Liveness probe
  curl ${SERVICE_URL}/health/liveness
  
  # Readiness probe (checks storage, auth, domains)
  curl ${SERVICE_URL}/health/readiness
  ```

- [ ] **Logs Reviewed**
  ```bash
  gcloud run services logs read supply-graph-ai \
    --region ${REGION} \
    --limit 50
  ```

- [ ] **Storage Access Verified** (via API)
  ```bash
  curl ${SERVICE_URL}/v1/api/utility/storage/status
  ```

### Quick Commands Reference

Complete command sequence for quick setup:

```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export BUCKET_NAME="supply-graph-ai-storage"
export SA_EMAIL="supply-graph-ai@${PROJECT_ID}.iam.gserviceaccount.com"

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  storage-component.googleapis.com \
  storage-api.googleapis.com

# Create service account
gcloud iam service-accounts create supply-graph-ai \
  --display-name="Supply Graph AI Service Account" \
  --description="Service account for Supply Graph AI Cloud Run service"

# Grant IAM roles (project-level)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# Create bucket
gcloud storage buckets create gs://${BUCKET_NAME} \
  --location=${REGION} \
  --uniform-bucket-level-access

# Grant storage permissions at bucket level (after bucket creation)
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.legacyBucketReader"

# Store secrets (optional - if not using environment variables)
echo -n "$PROJECT_ID" | gcloud secrets create gcp-project-id \
  --data-file=- \
  --replication-policy="automatic"

echo -n "$BUCKET_NAME" | gcloud secrets create gcp-storage-bucket \
  --data-file=- \
  --replication-policy="automatic"

# Grant service account access to secrets
gcloud secrets add-iam-policy-binding gcp-project-id \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gcp-storage-bucket \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# Optional: Pre-create directory structure
python scripts/setup_storage.py \
  --provider gcs \
  --bucket ${BUCKET_NAME} \
  --region ${REGION} \
  --project-id ${PROJECT_ID}

# Optional: Populate with synthetic data (requires conda environment)
# conda activate supply-graph-ai
# ome storage populate \
#   --provider gcs \
#   --bucket ${BUCKET_NAME} \
#   --region ${REGION} \
#   --project-id ${PROJECT_ID}

# Build and deploy using Artifact Registry
# First, ensure the repository exists
gcloud artifacts repositories describe cloud-run-source-deploy \
  --location=${REGION} --project=${PROJECT_ID} || \
gcloud artifacts repositories create cloud-run-source-deploy \
  --repository-format=docker \
  --location=${REGION} \
  --description="Docker repository for Cloud Run deployments" \
  --project=${PROJECT_ID}

# Build and push to Artifact Registry
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/supply-graph-ai:${TIMESTAMP}"
gcloud builds submit --tag ${IMAGE_TAG} --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/supply-graph-ai:latest

# Deploy using the Artifact Registry image
gcloud run deploy supply-graph-ai \
  --image ${IMAGE_TAG} \
  --service-account ${SA_EMAIL} \
  --region ${REGION} \
  --set-env-vars="STORAGE_PROVIDER=gcs,GCP_STORAGE_BUCKET=${BUCKET_NAME},GCP_PROJECT_ID=${PROJECT_ID},USE_SECRETS_MANAGER=true,SECRETS_PROVIDER=gcp" \
  --allow-unauthenticated

# Verify deployment
SERVICE_URL=$(gcloud run services describe supply-graph-ai \
  --region ${REGION} \
  --format 'value(status.url)')

curl ${SERVICE_URL}/health
curl ${SERVICE_URL}/health/readiness
```

---

## Prerequisites

Before starting, ensure you have:

- A GCP project with billing enabled
- `gcloud` CLI installed and authenticated
- Docker installed (for building container images)
- Access to create service accounts, buckets, and secrets

## Setup Order and Dependencies

### Bootstrapping Problem

The application has the following initialization order (from `src/core/main.py`):

1. **Storage Service** - Requires:
   - Storage bucket to exist
   - Storage credentials accessible
   - Directory structure (automatically created on first startup if missing)

2. **Authentication Service** - Requires:
   - API keys (optional, can be from secrets manager)

3. **Domain Components** - Requires:
   - Storage service to be initialized
   - Domain-specific storage handlers

### Critical Dependency Chain

```
GCP Project
    ↓
Service Account (with permissions)
    ↓
Storage Bucket (created manually)
    ↓
Secrets in Secret Manager (credentials stored)
    ↓
Directory Structure (auto-created on first startup, or pre-created via script)
    ↓
Synthetic Data (optional, populated via CLI after deployment)
    ↓
Cloud Run Service (configured to use service account)
    ↓
Application Startup (reads secrets, connects to storage, creates directories if needed)
```

**Key Insight**: The bucket, service account, and permissions must exist BEFORE the Cloud Run service is deployed, because:
- The application tries to connect to storage on startup (requires bucket-level permissions)
- The service account needs project-level permissions for Secret Manager access
- The service account needs bucket-level permissions for storage access (more secure than project-level)
- Secrets must be stored before the application can read them

## Manual Setup Steps

### Step 1: Create GCP Project and Enable APIs

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"  # or your preferred region

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    storage-component.googleapis.com \
    storage-api.googleapis.com
```

### Step 2: Create Service Account

Create a service account that Cloud Run will use:

```bash
# Create service account
gcloud iam service-accounts create supply-graph-ai \
    --display-name="Supply Graph AI Service Account" \
    --description="Service account for Supply Graph AI Cloud Run service"

# Get the service account email
export SA_EMAIL="supply-graph-ai@${PROJECT_ID}.iam.gserviceaccount.com"
```

### Step 3: Grant Service Account Permissions (Project-Level)

The service account needs project-level permissions for Secret Manager access. Storage permissions will be granted at the bucket level in Step 5 (after bucket creation).

```bash
# Grant Secret Manager Secret Accessor (read-only access to secrets)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"
```

**Note**: Storage permissions are granted at the bucket level (see Step 5) for better security, rather than at the project level.

### Step 4: Create Storage Bucket

**This must be done BEFORE deploying the application:**

```bash
# Set bucket name
export BUCKET_NAME="supply-graph-ai-storage"

# Create bucket
gcloud storage buckets create gs://${BUCKET_NAME} \
    --location=${REGION} \
    --uniform-bucket-level-access

# Verify bucket exists
gcloud storage buckets describe gs://${BUCKET_NAME}
```

### Step 5: Grant Storage Bucket Permissions

**This must be done AFTER creating the bucket:**

Grant the service account permissions to access the specific storage bucket. Bucket-level permissions are more secure than project-level permissions.

```bash
# Grant Storage Object Admin (for object read/write operations)
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectAdmin"

# Grant Storage Legacy Bucket Reader (for bucket metadata access)
# This is required for bucket.exists() checks during application startup
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.legacyBucketReader"
```

**Why both roles?**
- `roles/storage.objectAdmin`: Allows read/write access to objects in the bucket
- `roles/storage.legacyBucketReader`: Allows reading bucket metadata (required for `bucket.exists()` checks during startup)

### Step 6: Store Credentials in Secret Manager

For GCP, the application can use **Application Default Credentials (ADC)** when running on Cloud Run, which means you don't need to store service account keys. However, you may want to store other secrets:

```bash
# Store GCP Project ID (if not using environment variable)
echo -n "$PROJECT_ID" | gcloud secrets create gcp-project-id \
    --data-file=- \
    --replication-policy="automatic"

# Store storage bucket name (if not using environment variable)
echo -n "$BUCKET_NAME" | gcloud secrets create gcp-storage-bucket \
    --data-file=- \
    --replication-policy="automatic"

# Store any API keys you need
# Example: OpenAI API key
echo -n "your-api-key" | gcloud secrets create openai-api-key \
    --data-file=- \
    --replication-policy="automatic"

# Grant service account access to secrets
gcloud secrets add-iam-policy-binding gcp-project-id \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding gcp-storage-bucket \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding openai-api-key \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"
```

**Note**: For GCS access, the service account uses ADC, so you don't need to store GCS credentials in Secret Manager. The service account's IAM permissions (granted in Step 5) are sufficient.

### Step 7: Setup Storage Directory Structure

#### Bootstrapping Problem and Solutions

There's a potential bootstrapping issue: the directory structure needs to exist, but creating it traditionally required the application to be running. We've solved this with multiple approaches:

**Solution 1: Lazy Initialization (Recommended - Modern Best Practice)**

The application automatically creates the directory structure on first startup if it doesn't exist. This is the **default and recommended approach** because it:
- ✅ Eliminates manual setup steps
- ✅ Self-heals if structure is accidentally deleted
- ✅ Follows "convention over configuration" principles
- ✅ Reduces deployment complexity
- ✅ Aligns with modern Python API best practices (FastAPI, Django, Flask all use similar patterns)

**No action required** - the application handles this automatically on first startup.

**Solution 2: Standalone Setup Script (For Explicit Control)**

A standalone script (`scripts/setup_storage.py`) can be run independently before deployment:
- ✅ No dependency on running application
- ✅ Can be run as part of CI/CD pipeline
- ✅ Minimal dependencies (only storage libraries)
- ✅ Useful for infrastructure-as-code workflows

**Solution 3: Cloud Run Job (GCP-Native)**

Deploy a Cloud Run Job that runs once to set up storage:
- ✅ Uses same infrastructure as main service
- ✅ Can be scheduled or triggered manually
- ✅ Good for complex multi-step setup

**Solution 4: CI/CD Pipeline Step**

Include setup in your deployment pipeline:
- ✅ Automated and repeatable
- ✅ Part of deployment process
- ✅ Good for infrastructure-as-code

For most use cases, **Solution 1 (Lazy Initialization)** is recommended as it follows modern Python API best practices and eliminates the bootstrapping problem entirely.

**Note**: The application will automatically create the directory structure on first startup (lazy initialization). However, you can pre-create it using one of the options below if desired.

#### Option A: Standalone Setup Script (Recommended for Pre-Setup)

Use the standalone script that doesn't require the full application:

```bash
# Activate conda environment
conda activate supply-graph-ai

# Setup directory structure in GCS
python scripts/setup_storage.py \
    --provider gcs \
    --bucket $BUCKET_NAME \
    --region $REGION \
    --project-id $PROJECT_ID

# Or with explicit credentials
python scripts/setup_storage.py \
    --provider gcs \
    --bucket $BUCKET_NAME \
    --region $REGION \
    --credentials-json /path/to/credentials.json \
    --project-id $PROJECT_ID
```

**Advantages**:
- No dependency on running application
- Can be run as part of CI/CD pipeline
- Minimal dependencies (only storage libraries)

#### Option B: Using the CLI Commands

The CLI commands (`ome storage setup` and `ome storage populate`) can be used without the API server running. They use the application's storage libraries directly:

```bash
# Activate conda environment
conda activate supply-graph-ai

# Setup directory structure in GCS
ome storage setup \
    --provider gcs \
    --bucket $BUCKET_NAME \
    --region $REGION \
    --project-id $PROJECT_ID

# Optionally populate with synthetic data
# Note: Requires access to synth/synthetic-data/ directory
ome storage populate \
    --provider gcs \
    --bucket $BUCKET_NAME \
    --region $REGION \
    --project-id $PROJECT_ID
```

**What these commands require:**
- ✅ Application codebase and dependencies (via conda environment)
- ✅ Storage credentials (via environment variables or command-line flags)
- ✅ Access to `synth/synthetic-data/` directory (for populate command)
- ❌ **Does NOT require the API server to be running** - uses storage libraries directly

#### Option C: Automatic Lazy Initialization (Default)

The application automatically creates the directory structure on first startup if it doesn't exist. This is the **recommended approach** for modern Python APIs as it:
- Eliminates manual setup steps
- Self-heals if structure is missing
- Follows "convention over configuration" principles
- Reduces deployment complexity

**No action required** - the application handles this automatically.

**Important**: For any manual setup option, you need:
- GCP credentials configured locally (via `gcloud auth application-default login`)
- Or explicit credentials via `--credentials-json` flag
- The bucket must already exist

### Step 8: Configure Cloud Run Service

When deploying to Cloud Run, configure the service to:

1. Use the service account created in Step 2
2. Set environment variables
3. Enable Secret Manager access

```bash
# Option 1: Build and deploy separately (recommended for production)
# Build to Artifact Registry
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/supply-graph-ai:${TIMESTAMP}"
gcloud builds submit --tag ${IMAGE_TAG} --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/supply-graph-ai:latest

# Deploy using the built image
gcloud run deploy supply-graph-ai \
    --image ${IMAGE_TAG} \
    --service-account ${SA_EMAIL} \
    --region ${REGION} \
    --set-env-vars="STORAGE_PROVIDER=gcs,GCP_STORAGE_BUCKET=${BUCKET_NAME},GCP_PROJECT_ID=${PROJECT_ID},USE_SECRETS_MANAGER=true,SECRETS_PROVIDER=gcp" \
    --allow-unauthenticated  # or use --no-allow-unauthenticated for authenticated access

# Option 2: Build and deploy in one step (uses Artifact Registry automatically)
gcloud run deploy supply-graph-ai \
    --source . \
    --service-account ${SA_EMAIL} \
    --region ${REGION} \
    --set-env-vars="STORAGE_PROVIDER=gcs,GCP_STORAGE_BUCKET=${BUCKET_NAME},GCP_PROJECT_ID=${PROJECT_ID},USE_SECRETS_MANAGER=true,SECRETS_PROVIDER=gcp" \
    --allow-unauthenticated
```

Or use a YAML configuration file:

```yaml
# cloud-run-service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: supply-graph-ai
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "10"
    spec:
      serviceAccountName: supply-graph-ai@${PROJECT_ID}.iam.gserviceaccount.com
      containers:
        - image: ${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/supply-graph-ai:latest
        env:
        - name: STORAGE_PROVIDER
          value: "gcs"
        - name: GCP_STORAGE_BUCKET
          value: "${BUCKET_NAME}"
        - name: GCP_PROJECT_ID
          value: "${PROJECT_ID}"
        - name: USE_SECRETS_MANAGER
          value: "true"
        - name: SECRETS_PROVIDER
          value: "gcp"
        ports:
        - containerPort: 8001
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
```

## Service Account Configuration

### Required IAM Roles

The service account needs these roles:

| Role | Purpose | Required For |
|------|---------|--------------|
| `roles/storage.objectAdmin` | Read/write access to GCS objects | Storage operations |
| `roles/storage.legacyBucketReader` | Read bucket metadata | Bucket existence checks during startup |
| `roles/secretmanager.secretAccessor` | Read secrets from Secret Manager | API keys, configuration |

### Alternative: More Restrictive Permissions

The setup guide already uses bucket-level permissions (more secure than project-level). For even more restrictive permissions, you can use custom IAM roles or grant only the specific permissions needed:

```bash
# Storage: Bucket-level permissions (already done in Step 5)
# This is more secure than project-level permissions

# Secret Manager: Per-secret access (already done in Step 6)
# Each secret has individual IAM bindings for the service account
```

**Note**: The current setup already follows security best practices by:
- Using bucket-level IAM bindings instead of project-level
- Granting only the minimum required permissions
- Using per-secret IAM bindings for Secret Manager

### Service Account Key (Not Recommended for Cloud Run)

**Important**: For Cloud Run, you should NOT create and download service account keys. Cloud Run automatically uses the service account's identity via Application Default Credentials (ADC).

If you need to test locally with the same credentials:

```bash
# Create a key (for local testing only, not for Cloud Run)
gcloud iam service-accounts keys create ./gcp-credentials.json \
    --iam-account=${SA_EMAIL}

# Use it locally
export GOOGLE_APPLICATION_CREDENTIALS="./gcp-credentials.json"
```

**Security Note**: Never commit service account keys to version control. Use Secret Manager or environment variables instead.

## Storage Setup

### Directory Structure

The storage setup creates this simplified structure:

```
gs://your-bucket/
├── okh/
│   └── manifests/
│       └── .gitkeep
├── okw/
│   └── facilities/
│       └── .gitkeep
└── supply-trees/
    └── .gitkeep
```

The `.gitkeep` files are placeholder files that establish the directory structure in blob storage (which doesn't have true directories).

### Verification

Verify the directory structure was created:

```bash
# List objects in bucket
gsutil ls -r gs://${BUCKET_NAME}/

# Check for placeholder files
gsutil ls gs://${BUCKET_NAME}/okh/manifests/*/
```

## Secrets Manager Setup

### Secret Naming Convention

The application expects secrets to be named using lowercase with hyphens:

- `OPENAI_API_KEY` → `openai-api-key`
- `GCP_PROJECT_ID` → `gcp-project-id`
- `GCP_STORAGE_BUCKET` → `gcp-storage-bucket`

### How Secrets Are Resolved

1. **In Cloud Run (GCP environment)**:
   - Auto-detects GCP Secret Manager (via `K_SERVICE` or `GOOGLE_CLOUD_PROJECT`)
   - Tries to read from Secret Manager first
   - Falls back to environment variables

2. **Local Development**:
   - Uses environment variables by default
   - Can enable Secret Manager with `USE_SECRETS_MANAGER=true`

### Required Secrets

| Secret Name | Environment Variable | Required | Purpose |
|-------------|---------------------|----------|---------|
| `gcp-project-id` | `GCP_PROJECT_ID` | Yes | GCP project identifier |
| `gcp-storage-bucket` | `GCP_STORAGE_BUCKET` | Yes | Storage bucket name |
| `openai-api-key` | `OPENAI_API_KEY` | Optional | OpenAI API access |
| `anthropic-api-key` | `ANTHROPIC_API_KEY` | Optional | Anthropic API access |

## Application Configuration

### Environment Variables

The application reads configuration from environment variables (with Secret Manager fallback):

```bash
# Required
STORAGE_PROVIDER=gcs
GCP_PROJECT_ID=your-project-id
GCP_STORAGE_BUCKET=your-bucket-name

# Optional
USE_SECRETS_MANAGER=true
SECRETS_PROVIDER=gcp
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Startup Sequence

When the application starts:

1. **Detects Environment**: Checks for `K_SERVICE` (Cloud Run) or `GOOGLE_CLOUD_PROJECT`
2. **Initializes Secrets Manager**: Auto-detects GCP Secret Manager
3. **Loads Configuration**: Reads from environment variables and secrets
4. **Connects to Storage**: Uses Application Default Credentials (ADC) to authenticate
5. **Verifies Bucket**: Checks that bucket exists and is accessible
6. **Initializes Services**: Sets up storage, authentication, and domain services

### Startup Failures

Common startup failures and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `Bucket not found` | Bucket doesn't exist | Create bucket (Step 4) |
| `Permission denied` | Service account lacks permissions | Grant project-level IAM roles (Step 3) and bucket-level permissions (Step 5) |
| `Secret not found` | Secret doesn't exist in Secret Manager | Create secret (Step 6) |
| `Directory structure missing` | Placeholder files not created | Application will auto-create on startup, or run setup script (Step 7) |

## Verification

### Pre-Deployment Checklist

See the [Quick Reference Checklist](#quick-reference-checklist) at the top of this document for a complete checklist.

### Post-Deployment Verification

```bash
# Check Cloud Run service status
gcloud run services describe supply-graph-ai --region ${REGION}

# Check service logs
gcloud run services logs read supply-graph-ai --region ${REGION} --limit 50

# Test health endpoint
curl https://your-service-url.run.app/health

# Test readiness endpoint
curl https://your-service-url.run.app/health/readiness

# Test storage access (via API)
curl https://your-service-url.run.app/v1/api/utility/storage/status
```

### Troubleshooting

#### Service Won't Start

1. Check logs: `gcloud run services logs read supply-graph-ai --region ${REGION}`
2. Verify service account: Check IAM bindings
3. Verify bucket exists: `gsutil ls gs://${BUCKET_NAME}`
4. Verify secrets: `gcloud secrets versions access latest --secret="gcp-project-id"`

#### Permission Denied Errors

1. Verify service account has roles:
   ```bash
   gcloud projects get-iam-policy $PROJECT_ID \
       --flatten="bindings[].members" \
       --filter="bindings.members:serviceAccount:${SA_EMAIL}"
   ```

2. Check bucket IAM:
   ```bash
   gcloud storage buckets get-iam-policy gs://${BUCKET_NAME}
   ```

3. Check secret access:
   ```bash
   gcloud secrets get-iam-policy gcp-project-id
   ```

## Summary

The correct setup order is:

1. **Infrastructure**: Project, APIs, Service Account (Steps 1-2)
2. **Permissions**: Grant project-level IAM roles for Secret Manager (Step 3)
3. **Storage**: Create bucket, then grant bucket-level permissions (Steps 4-5)
4. **Secrets**: Store credentials in Secret Manager (Step 6)
5. **Directory Structure**: Auto-created on first startup, or pre-created via script (Step 7)
6. **Application**: Deploy to Cloud Run with service account (Step 8)
7. **Verification**: Test endpoints and functionality

**Key Principles**:
- All infrastructure (bucket, service account, secrets) must exist BEFORE the application is deployed
- Storage permissions are granted at the bucket level (more secure than project-level)
- Directory structure is automatically created on first startup (lazy initialization)
- The application self-bootstraps, eliminating manual setup steps

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `Bucket not found` | Bucket doesn't exist | Create bucket before deploying (Step 4) |
| `Permission denied` | Service account lacks permissions | Grant project-level IAM roles (Step 3) and bucket-level permissions (Step 5) |
| `Secret not found` | Secret doesn't exist in Secret Manager | Create secret (Step 6) |
| `Directory structure missing` | Placeholder files not created | Application will auto-create on startup, or run setup script (Step 7) |
| `Service account not found` | Service account doesn't exist | Create service account before deployment (Step 2) |

