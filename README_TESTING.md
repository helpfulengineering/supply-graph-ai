# Direct Cloud Run Testing

This directory contains scripts for testing the Cloud Run service directly, bypassing the CI/CD pipeline.

## Scripts

### `test_cloud_run_direct.py`
Direct testing script that sends requests to the deployed Cloud Run service and helps debug 500 errors.

**Usage:**
```bash
# Set the service URL (defaults to the production URL)
export SERVICE_URL="https://supply-graph-ai-1085931013579.us-west1.run.app"
export USE_AUTH=true

# Run the tests
python test_cloud_run_direct.py
```

**What it tests:**
- List OKH manifests (to check storage service)
- Create OKH manifest
- Create OKW facility
- Match OKH to OKW (if OKH creation succeeds)

### `check_cloud_logs.sh`
Helper script to check Cloud Run logs for errors.

**Usage:**
```bash
# Set project and service name (optional, has defaults)
export PROJECT_ID="nathan-playground-368310"
export SERVICE_NAME="supply-graph-ai"

# Run the script
./check_cloud_logs.sh
```

**What it shows:**
- Recent ERROR level logs
- Logs with "Error" or "Exception" in text
- Recent 500 errors
- Full tracebacks for recent errors

## Workflow

1. **Run the test script:**
   ```bash
   python test_cloud_run_direct.py
   ```

2. **If you see 500 errors, check the logs:**
   ```bash
   ./check_cloud_logs.sh
   ```

3. **Or check logs manually:**
   ```bash
   # View recent errors
   gcloud logging read \
     'resource.type=cloud_run_revision AND resource.labels.service_name=supply-graph-ai AND severity>=ERROR' \
     --limit 50 --format json \
     --project=nathan-playground-368310
   ```

4. **Fix the issues found in the logs**

5. **Re-run the test script to verify fixes**

## Authentication

The scripts use GCP identity tokens for authentication. Make sure you're authenticated:

```bash
gcloud auth login
gcloud auth application-default login
```

Or set an explicit token:
```bash
export IDENTITY_TOKEN=$(gcloud auth print-identity-token)
```
