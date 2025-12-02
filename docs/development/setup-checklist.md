# Cloud Deployment Setup Checklist

> **Note**: This is a quick reference. For complete setup instructions, see the [GCP Cloud Run Setup Guide](./gcp-cloud-run-setup.md).

This document provides a quick checklist for setting up a new cloud environment. For detailed explanations, step-by-step instructions, and troubleshooting, refer to the [main setup guide](./gcp-cloud-run-setup.md).

## Quick Checklist

### Phase 1: Infrastructure Setup

- [ ] GCP project created with billing enabled
- [ ] Required APIs enabled (Cloud Run, Secret Manager, Storage)
- [ ] Service account created with correct IAM roles
- [ ] Storage bucket created

### Phase 2: Secrets and Configuration

- [ ] Secrets stored in Secret Manager
- [ ] Service account has access to secrets

### Phase 3: Storage Initialization (Optional)

- [ ] Directory structure (auto-created on first startup, or pre-created via script)
- [ ] Synthetic data populated (optional)

### Phase 4: Application Deployment

- [ ] Container image built and pushed
- [ ] Deployed to Cloud Run with correct configuration

### Phase 5: Verification

- [ ] Service status checked
- [ ] Health endpoints tested
- [ ] Logs reviewed

## Quick Commands

```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export BUCKET_NAME="supply-graph-ai-storage"
export SA_EMAIL="supply-graph-ai@${PROJECT_ID}.iam.gserviceaccount.com"

# Create service account
gcloud iam service-accounts create supply-graph-ai

# Grant roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# Create bucket
gcloud storage buckets create gs://${BUCKET_NAME} --location=${REGION}

# Optional: Pre-create directory structure
python scripts/setup_storage.py --provider gcs --bucket ${BUCKET_NAME} --region ${REGION}

# Deploy
gcloud run deploy supply-graph-ai \
  --source . \
  --service-account ${SA_EMAIL} \
  --region ${REGION} \
  --set-env-vars="STORAGE_PROVIDER=gcs,GCP_STORAGE_BUCKET=${BUCKET_NAME},GCP_PROJECT_ID=${PROJECT_ID},USE_SECRETS_MANAGER=true"
```

## Important Notes

- **Never create service account keys for Cloud Run** - Use IAM roles instead
- **Bucket must exist before deployment** - Application connects on startup
- **Directory structure auto-created** - Application creates it on first startup (lazy initialization)
- **Secrets must be accessible** - Service account needs `secretAccessor` role
- **Test locally first** - Use `gcloud auth application-default login` for local testing

For complete documentation, see [GCP Cloud Run Setup Guide](./gcp-cloud-run-setup.md).
