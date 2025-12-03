# CI/CD Deployment Permissions

## Overview

For CI/CD deployment to Cloud Run, the service account used in GitHub Actions needs specific IAM permissions to deploy services.

## Required Permissions

The service account needs the **Cloud Run Admin** role to deploy services, and permission to act as itself:

```bash
export PROJECT_ID="nathan-playground-368310"
export SA_EMAIL="supply-graph-ai@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant Cloud Run Admin role (includes all necessary permissions)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.admin"

# Grant permission to act as the service account itself (required for deployment)
gcloud iam service-accounts add-iam-policy-binding ${SA_EMAIL} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"

# Grant permission to act as the Compute Engine default service account
# (required even when specifying a different service account)
# Note: The Compute Engine default SA uses PROJECT_NUMBER, not PROJECT_ID
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
export COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud iam service-accounts add-iam-policy-binding ${COMPUTE_SA} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"
```

## What This Role Includes

The `roles/run.admin` role includes all necessary permissions for Cloud Run deployment:
- `run.services.get` - Get service information
- `run.services.create` - Create new services
- `run.services.update` - Update existing services
- `run.services.delete` - Delete services (if needed)
- `run.revisions.create` - Create new revisions
- `run.revisions.get` - Get revision information
- `run.revisions.update` - Update revisions
- `iam.serviceAccounts.actAs` - Act as the runtime service account
- And other Cloud Run management permissions

## Alternative: Minimum Required Permissions

If you prefer to grant only the minimum required permissions instead of the full admin role:

```bash
# Grant individual permissions (more granular control)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.developer"

# Also need to act as the service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"
```

However, `roles/run.admin` is recommended for CI/CD deployments as it provides all necessary permissions in one role.

## Verify Permissions

After granting permissions, verify the service account has the required role:

```bash
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:${SA_EMAIL}" \
    --format="table(bindings.role)"
```

You should see `roles/run.admin` (or the individual permissions) in the output.

## Artifact Registry Permissions

The service account also needs permission to push images to Artifact Registry:

```bash
# Grant Artifact Registry Writer role (for pushing images)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/artifactregistry.writer"
```

## Summary of All Required Permissions

Your service account needs:
1. `roles/run.admin` - For Cloud Run deployment operations
2. `roles/iam.serviceAccountUser` on itself - To act as itself during deployment
3. `roles/iam.serviceAccountUser` on Compute Engine default SA - Required by Cloud Run
4. `roles/artifactregistry.writer` - To push images to Artifact Registry

## Important Notes

1. **Separate Service Accounts**: Consider using a separate service account for CI/CD deployment (e.g., `ci-cd-deployer@...`) rather than the runtime service account. This follows the principle of least privilege.

2. **Service Account User Role**: If deploying with a different service account than the runtime service account, you may also need `roles/iam.serviceAccountUser` to allow the deployment service account to act as the runtime service account.

3. **Region-Specific**: Cloud Run permissions are typically project-wide, but ensure the service account has access to the specific region where you're deploying.

## Troubleshooting

If you still get permission errors after granting `roles/run.admin`:

1. **Wait a few minutes** - IAM policy changes can take a few minutes to propagate
2. **Verify the service account email** - Ensure you're using the correct service account
3. **Check project ID** - Ensure you're granting permissions in the correct project
4. **Verify API is enabled** - Ensure Cloud Run API is enabled:
   ```bash
   gcloud services enable run.googleapis.com
   ```

