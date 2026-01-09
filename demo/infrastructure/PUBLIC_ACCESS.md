# Configuring Public Access for Demo (Task 1.1.3)

This document describes how to configure public access for the Cloud Run deployment to enable unauthenticated access for the demo.

## Current Status

- **Service**: `supply-graph-ai`
- **Region**: `us-west1`
- **URL**: `https://supply-graph-ai-1085931013579.us-west1.run.app`
- **Current Access**: Requires authentication (403 responses)
- **Target**: Public access for demo endpoints

## Method 1: Using the Configuration Script (Recommended)

### Prerequisites
- `gcloud` CLI installed and authenticated
- Access to the GCP project
- Permissions to modify Cloud Run IAM policies

### Steps

1. **Check current access status:**
   ```bash
   python -m demo.infrastructure.configure_public_access --check
   ```

2. **Configure public access:**
   ```bash
   python -m demo.infrastructure.configure_public_access
   ```

3. **Verify public access:**
   ```bash
   python -m demo.infrastructure.verify_deployment
   ```

4. **Run tests to verify:**
   ```bash
   pytest tests/demo/test_public_access.py -v
   ```

### Removing Public Access (After Demo)

To restore authentication requirements after the demo:

```bash
python -m demo.infrastructure.configure_public_access --remove
```

## Method 2: Manual Configuration via gcloud CLI

### Steps

1. **Check current IAM policy:**
   ```bash
   gcloud run services get-iam-policy supply-graph-ai \
     --region=us-west1
   ```

2. **Add public access (allUsers):**
   ```bash
   gcloud run services add-iam-policy-binding supply-graph-ai \
     --region=us-west1 \
     --member=allUsers \
     --role=roles/run.invoker
   ```

3. **Verify public access:**
   ```bash
   curl https://supply-graph-ai-1085931013579.us-west1.run.app/health
   ```
   
   Should return `200 OK` instead of `403 Forbidden`.

### Removing Public Access (After Demo)

```bash
gcloud run services remove-iam-policy-binding supply-graph-ai \
  --region=us-west1 \
  --member=allUsers \
  --role=roles/run.invoker
```

## Method 3: Update CI/CD Workflow

To make public access permanent in the deployment pipeline, update `.github/workflows/ci-cd.yml`:

**Current configuration (line 460):**
```bash
"--no-allow-unauthenticated"
```

**Change to:**
```bash
"--allow-unauthenticated"
```

**Note**: This changes the deployment to always allow unauthenticated access. For demo-only public access, use Method 1 or 2 instead.

## Security Considerations

⚠️ **Important**: Public access means anyone on the internet can call your API endpoints.

### For Demo:
- ✅ Acceptable for demo purposes with synthetic data
- ✅ Can be removed after demo
- ✅ No sensitive data exposed

### For Production:
- ❌ **NOT recommended** for production deployments
- ❌ Consider rate limiting if public access is needed
- ❌ Monitor for abuse
- ❌ Use authentication for production workloads

## Verification

### Test Public Access

Run the public access tests:

```bash
pytest tests/demo/test_public_access.py -v
```

### Manual Verification

Test endpoints without authentication:

```bash
# Health endpoint
curl https://supply-graph-ai-1085931013579.us-west1.run.app/health

# Should return 200 OK (not 403 Forbidden)
```

## Troubleshooting

### Issue: Still getting 403 after configuration

**Possible causes:**
1. IAM policy changes take a few seconds to propagate
2. Service may need to be restarted
3. Check IAM policy: `gcloud run services get-iam-policy supply-graph-ai --region=us-west1`

**Solution:**
- Wait 30-60 seconds and retry
- Verify IAM binding exists: `gcloud run services get-iam-policy supply-graph-ai --region=us-west1 | grep allUsers`

### Issue: Permission denied when running script

**Solution:**
- Ensure you're authenticated: `gcloud auth login`
- Ensure you have Cloud Run Admin role: `roles/run.admin`
- Check project: `gcloud config get-value project`

### Issue: Service returns 503

**Possible causes:**
1. Service is starting up
2. Service is experiencing issues
3. Service is scaled to zero and cold-starting

**Solution:**
- Wait a few minutes and retry
- Check service status: `gcloud run services describe supply-graph-ai --region=us-west1`
- Check logs: `gcloud logging read "resource.type=cloud_run_revision" --limit=50`

## Post-Demo Cleanup

After the demo, restore authentication requirements:

```bash
python -m demo.infrastructure.configure_public_access --remove
```

Or manually:

```bash
gcloud run services remove-iam-policy-binding supply-graph-ai \
  --region=us-west1 \
  --member=allUsers \
  --role=roles/run.invoker
```

## Related Files

- `demo/infrastructure/configure_public_access.py` - Configuration script
- `demo/infrastructure/verify_deployment.py` - Verification script
- `tests/demo/test_public_access.py` - Public access tests
- `.github/workflows/ci-cd.yml` - CI/CD deployment configuration
