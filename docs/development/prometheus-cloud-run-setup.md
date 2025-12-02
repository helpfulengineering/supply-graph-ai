# Prometheus on Cloud Run Setup

This guide explains how to deploy Prometheus to Cloud Run for scraping metrics from the supply-graph-ai service.

## Overview

Prometheus is deployed as a separate Cloud Run service that scrapes metrics from the supply-graph-ai service. This provides a cloud-native monitoring solution.

## File Structure

All Prometheus Cloud Run deployment files are located in `deploy/prometheus/`:

- `Dockerfile` - Docker image definition
- `entrypoint.sh` - Entrypoint script that generates Prometheus config at runtime
- `deploy.sh` - Deployment script for Cloud Run

## Prerequisites

- GCP project with Cloud Run and Artifact Registry enabled
- `gcloud` CLI configured with appropriate permissions
- Docker installed (for local testing)

## Quick Deployment

```bash
# Set your configuration
export PROJECT_ID=nathan-playground-368310
export REGION=us-west1
export TARGET_SERVICE_URL=supply-graph-ai-1085931013579.us-west1.run.app

# Deploy Prometheus
./deploy/prometheus/deploy.sh
```

## Manual Deployment Steps

### 1. Build and Push Image

The deployment script handles this automatically, but if you need to build manually:

```bash
PROJECT_ID=your-project-id
REGION=us-west1
IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/prometheus:latest"

# Build from the deploy/prometheus directory
cd deploy/prometheus
gcloud builds submit \
  --tag ${IMAGE_TAG} \
  --project ${PROJECT_ID} \
  .
```

### 2. Deploy to Cloud Run

```bash
gcloud run deploy prometheus-supply-graph-ai \
  --image ${IMAGE_TAG} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 1 \
  --set-env-vars="TARGET_SERVICE_URL=supply-graph-ai-1085931013579.us-west1.run.app" \
  --project ${PROJECT_ID}
```

### 3. Get Service URL

```bash
SERVICE_URL=$(gcloud run services describe prometheus-supply-graph-ai \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(status.url)')

echo "Prometheus UI: $SERVICE_URL"
```

## Configuration

### Prometheus Config

The Prometheus configuration is generated dynamically at runtime by the entrypoint script (`deploy/prometheus/entrypoint.sh`). The configuration includes:

- **Scrape Interval**: 15 seconds (configurable via `SCRAPE_INTERVAL` env var)
- **Target**: Your Cloud Run service URL (set via `TARGET_SERVICE_URL` env var)
- **Metrics Path**: `/v1/api/utility/metrics?format=prometheus`
- **Scheme**: HTTPS (required for Cloud Run)

### Environment Variables

- `TARGET_SERVICE_URL`: The Cloud Run service to scrape (without https://)
- `PORT`: Set by Cloud Run automatically (Prometheus listens on this port)

## Accessing Prometheus

Once deployed, access the Prometheus UI:

- **Main UI**: `https://your-prometheus-service.run.app`
- **Targets**: `https://your-prometheus-service.run.app/targets`
- **Graph**: `https://your-prometheus-service.run.app/graph`
- **Alerts**: `https://your-prometheus-service.run.app/alerts`

## Verifying Scraping

### Check Targets

```bash
# Get Prometheus service URL
PROM_URL=$(gcloud run services describe prometheus-supply-graph-ai \
  --region us-west1 \
  --format 'value(status.url)')

# Check targets
curl "${PROM_URL}/api/v1/targets" | jq '.data.activeTargets[]'
```

### Query Metrics

```bash
# Query total requests
curl "${PROM_URL}/api/v1/query?query=http_requests_total" | jq

# Query request rate
curl "${PROM_URL}/api/v1/query?query=rate(http_requests_total[5m])" | jq
```

## Important Notes

### Storage Limitations

⚠️ **Cloud Run doesn't provide persistent storage**. Prometheus metrics are stored in memory and will be lost when the container restarts. For production use, consider:

1. **Cloud Monitoring Integration**: Use GCP's managed Prometheus service
2. **External Storage**: Configure Prometheus to use remote storage (e.g., Thanos, Cortex)
3. **GKE Deployment**: Deploy Prometheus in GKE with persistent volumes

### Resource Limits

- **Memory**: 512Mi (adjust if needed)
- **CPU**: 1 vCPU
- **Max Instances**: 1 (to avoid duplicate scraping)

### Cost Considerations

- Cloud Run charges for CPU and memory usage
- Prometheus running 24/7 will incur costs
- Consider using Cloud Monitoring's managed Prometheus for production

## Troubleshooting

### Targets Show as DOWN

1. **Check target URL**:
   ```bash
   # Verify the target service is accessible
   curl https://supply-graph-ai-1085931013579.us-west1.run.app/v1/api/utility/metrics?format=prometheus
   ```

2. **Check Prometheus logs**:
   ```bash
   gcloud run services logs read prometheus-supply-graph-ai \
     --region us-west1 \
     --limit 50
   ```

3. **Verify configuration**:
   - Ensure `TARGET_SERVICE_URL` is set correctly
   - Check that the target service allows unauthenticated access (or configure auth)

### Metrics Not Appearing

1. **Wait for scrape interval**: Metrics appear after the first scrape (15 seconds)
2. **Check scrape errors**: Look at Prometheus logs for scrape errors
3. **Verify metrics endpoint**: Test the metrics endpoint directly

### Port Issues

If Prometheus doesn't start, check that the PORT environment variable is being used correctly. The entrypoint script should handle this automatically.

## Next Steps

1. **Set up Alerting Rules**: Create alert rules for error rates, latency, etc.
2. **Configure Grafana**: Connect Grafana to Prometheus for visualization
3. **Remote Storage**: Set up remote storage for long-term metric retention
4. **Cloud Monitoring Integration**: Consider migrating to GCP's managed Prometheus

## Alternative: Cloud Monitoring Managed Prometheus

For production, consider using GCP's managed Prometheus service:

1. Enable Managed Prometheus in Cloud Monitoring
2. Configure scrape jobs via Cloud Console
3. Access metrics via Cloud Monitoring API
4. Integrate with Grafana using Cloud Monitoring data source

This provides:
- Persistent storage
- High availability
- Automatic scaling
- Integration with other GCP services

