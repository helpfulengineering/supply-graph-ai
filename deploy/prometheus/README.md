# Prometheus Cloud Run Deployment

This directory contains all files needed to deploy Prometheus to Google Cloud Run for monitoring the supply-graph-ai service.

## Files

- **`Dockerfile`** - Docker image definition based on official Prometheus image
- **`entrypoint.sh`** - Entrypoint script that generates Prometheus configuration at runtime from environment variables
- **`deploy.sh`** - Deployment script that builds and deploys Prometheus to Cloud Run

## Quick Start

```bash
# Set configuration
export PROJECT_ID=your-project-id
export REGION=us-west1
export TARGET_SERVICE_URL=your-service-url.run.app

# Deploy
./deploy.sh
```

## How It Works

1. **Build**: The `deploy.sh` script creates a minimal build context with just the Dockerfile and entrypoint script
2. **Image**: Builds a Docker image using the official `prom/prometheus:latest` base image
3. **Config**: The entrypoint script generates Prometheus configuration at runtime from environment variables
4. **Deploy**: Deploys the image to Cloud Run with appropriate resource limits

## Environment Variables

- `TARGET_SERVICE_URL` - The Cloud Run service URL to scrape (without https://)
- `PORT` - Set automatically by Cloud Run (defaults to 9090)
- `SCRAPE_INTERVAL` - Scrape interval (defaults to 15s)

## Documentation

For detailed setup instructions, see [docs/development/prometheus-cloud-run-setup.md](../../docs/development/prometheus-cloud-run-setup.md).

