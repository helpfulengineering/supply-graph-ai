# Cloud Run Verification Guide

This guide covers how to verify logging, secrets manager, and Prometheus integration for the supply-graph-ai service running on GCP Cloud Run.

## Quick Verification

Run the automated verification script:

```bash
export SERVICE_URL=https://your-service-url.run.app
export SERVICE_NAME=supply-graph-ai
export REGION=us-west1
export PROJECT_ID=your-project-id

./scripts/verify-cloud-run.sh
```

## Manual Verification Steps

### 1. Cloud Logging Verification

#### Check Logs via gcloud CLI

```bash
# View recent logs
gcloud run services logs read supply-graph-ai \
  --region us-west1 \
  --project your-project-id \
  --limit 50

# Filter for specific log levels
gcloud run services logs read supply-graph-ai \
  --region us-west1 \
  --project your-project-id \
  --filter='severity>=ERROR' \
  --limit 20

# View logs in JSON format
gcloud run services logs read supply-graph-ai \
  --region us-west1 \
  --project your-project-id \
  --format=json \
  --limit 10 | jq '.'
```

#### Check Logs via Cloud Console

1. Open [Cloud Logging Console](https://console.cloud.google.com/logs/query)
2. Filter by resource type: `resource.type="cloud_run_revision"`
3. Filter by service: `resource.labels.service_name="supply-graph-ai"`
4. Verify logs show:
   - `severity` field (INFO, WARNING, ERROR, etc.)
   - `timestamp` in ISO 8601 format
   - Structured JSON payloads
   - Service metadata (`resource.labels.service_name`)

#### Expected Log Structure

```json
{
  "severity": "INFO",
  "timestamp": "2025-12-01T20:37:39.932012Z",
  "resource": {
    "type": "cloud_run_revision",
    "labels": {
      "service_name": "supply-graph-ai",
      "revision_name": "supply-graph-ai-00004-dmc",
      "location": "us-west1"
    }
  },
  "jsonPayload": {
    "message": "Request completed",
    "request_id": "abc123",
    "status_code": 200
  }
}
```

### 2. Secret Manager Verification

#### Check for Secret Manager Initialization

```bash
# Search logs for Secret Manager initialization
gcloud run services logs read supply-graph-ai \
  --region us-west1 \
  --project your-project-id \
  --filter='textPayload=~"Secret Manager" OR jsonPayload.message=~"Secret Manager"' \
  --limit 10

# Check for GCP Secret Manager client initialization
gcloud run services logs read supply-graph-ai \
  --region us-west1 \
  --project your-project-id \
  --filter='textPayload=~"Initialized GCP Secret Manager" OR jsonPayload.message=~"Initialized GCP Secret Manager"' \
  --limit 5
```

#### Expected Log Messages

Look for:
- `"Initialized GCP Secret Manager client for project ..."`
- `"Using Application Default Credentials"` (if using ADC)
- No errors about missing `google-cloud-secret-manager` package

#### Verify Secrets Are Accessible

```bash
# List secrets in Secret Manager
gcloud secrets list --project your-project-id

# Check service account has access
gcloud secrets get-iam-policy secret-name \
  --project your-project-id

# Test reading a secret (if you have permissions)
gcloud secrets versions access latest --secret=secret-name \
  --project your-project-id
```

### 3. Prometheus Integration

#### Option 1: Local Prometheus (Recommended for Testing)

1. **Update Prometheus configuration**:
   ```bash
   # Edit config/prometheus-cloud-run.yml
   # Update the target URL to your Cloud Run service
   ```

2. **Run Prometheus locally**:
   ```bash
   # Using Docker
   docker run -d \
     --name prometheus-cloud-run \
     -p 9090:9090 \
     -v $(pwd)/config/prometheus-cloud-run.yml:/etc/prometheus/prometheus.yml:ro \
     prom/prometheus:latest
   
   # Or using local Prometheus binary
   prometheus --config.file=config/prometheus-cloud-run.yml
   ```

3. **Verify scraping**:
   ```bash
   # Check target status
   curl http://localhost:9090/api/v1/targets | \
     jq '.data.activeTargets[] | select(.labels.job=="supply-graph-ai-cloud-run")'
   
   # Query metrics
   curl 'http://localhost:9090/api/v1/query?query=http_requests_total'
   ```

4. **Access Prometheus UI**:
   - Open http://localhost:9090
   - Navigate to Status → Targets
   - Verify `supply-graph-ai-cloud-run` target shows as UP
   - Use Graph tab to query metrics

#### Option 2: Cloud Monitoring Managed Prometheus

1. **Enable Managed Prometheus**:
   ```bash
   gcloud services enable monitoring.googleapis.com \
     --project your-project-id
   ```

2. **Configure scraping** (via Cloud Console):
   - Navigate to Cloud Monitoring → Prometheus
   - Create scrape configuration for Cloud Run service
   - Configure target: `https://your-service-url.run.app/v1/api/utility/metrics?format=prometheus`

3. **Verify metrics**:
   - Check Cloud Monitoring → Metrics Explorer
   - Query: `prometheus_target_scrapes_sample_limit_exceeded_total`

#### Option 3: Prometheus in GKE

If you have a GKE cluster:

1. **Deploy Prometheus**:
   ```bash
   # Use Prometheus Operator or Helm chart
   helm install prometheus prometheus-community/kube-prometheus-stack
   ```

2. **Configure ServiceMonitor**:
   ```yaml
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: supply-graph-ai
   spec:
     endpoints:
     - interval: 15s
       path: /v1/api/utility/metrics
       params:
         format: ['prometheus']
       scheme: https
     selector:
       matchLabels:
         app: supply-graph-ai
   ```

## Troubleshooting

### Logs Not Appearing

1. **Check service is running**:
   ```bash
   gcloud run services describe supply-graph-ai \
     --region us-west1 \
     --project your-project-id
   ```

2. **Check logging configuration**:
   - Verify `LOG_LEVEL` environment variable is set
   - Check that logs are being written to stdout/stderr (not files)

3. **Check IAM permissions**:
   - Service account needs `roles/logging.logWriter` role
   - Cloud Run automatically grants this, but verify if logs are missing

### Secret Manager Not Working

1. **Check package is installed**:
   ```bash
   # Check logs for import errors
   gcloud run services logs read supply-graph-ai \
     --region us-west1 \
     --filter='textPayload=~"google-cloud-secret-manager" OR textPayload=~"ImportError"'
   ```

2. **Verify environment variables**:
   - `USE_SECRETS_MANAGER=true`
   - `SECRETS_PROVIDER=gcp`
   - `GCP_PROJECT_ID` or `GOOGLE_CLOUD_PROJECT` is set

3. **Check service account permissions**:
   ```bash
   gcloud projects get-iam-policy your-project-id \
     --flatten="bindings[].members" \
     --filter="bindings.members:serviceAccount:supply-graph-ai@your-project-id.iam.gserviceaccount.com"
   ```

### Prometheus Target Down

1. **Verify metrics endpoint is accessible**:
   ```bash
   curl https://your-service-url.run.app/v1/api/utility/metrics?format=prometheus
   ```

2. **Check Prometheus can reach Cloud Run**:
   - Cloud Run services are publicly accessible by default
   - If using authentication, configure Prometheus with credentials

3. **Check Prometheus logs**:
   ```bash
   docker logs prometheus-cloud-run
   ```

4. **Verify configuration**:
   ```bash
   # Test Prometheus config
   promtool check config config/prometheus-cloud-run.yml
   ```

## Example Queries

### Prometheus Queries

```promql
# Total requests
http_requests_total

# Requests per second
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Request duration (95th percentile)
histogram_quantile(0.95, http_request_duration_seconds_bucket)

# Requests by endpoint
sum by (path) (http_requests_total)
```

### Cloud Logging Queries

```
resource.type="cloud_run_revision"
resource.labels.service_name="supply-graph-ai"
severity>=WARNING
```

## Next Steps

- Set up alerting rules in Prometheus
- Create Grafana dashboards for visualization
- Configure Cloud Monitoring alerts
- Set up log-based metrics in Cloud Logging

