# Backup Deployment Runbook

This document provides step-by-step instructions for setting up and using the local Docker deployment as a backup for the demo.

## Overview

The backup deployment runs the OHM API locally using Docker Compose, accessible at `http://localhost:8001`. This serves as a fallback option if Cloud Run is unavailable during the demo.

## Prerequisites

- Docker and Docker Compose installed
- `.env` file configured (or environment variables set)
- Port 8001 available on localhost

## Quick Start

### 1. Start the Deployment

```bash
# From project root
docker-compose up -d
```

This starts the `ohm-api` service in detached mode.

### 2. Verify Deployment

```bash
# Run verification script
python -m demo.infrastructure.verify_local_deployment

# Or check health directly
curl http://localhost:8001/health
```

### 3. Stop the Deployment

```bash
docker-compose down
```

## Detailed Setup

### Step 1: Review Configuration

The deployment uses `docker-compose.yml` with the following key settings:

- **Service**: `ohm-api`
- **Port**: `8001` (mapped from container port 8001)
- **Environment**: Loads from `.env` file
- **Storage**: Uses Docker volume `ohm-storage`
- **Network**: `ohm-network` (bridge)

### Step 2: Configure Environment

Ensure your `.env` file contains necessary configuration:

```bash
# Core API settings
API_HOST=0.0.0.0
API_PORT=8001
PORT=8001
DEBUG=false
LOG_LEVEL=INFO
ENVIRONMENT=development

# CORS and security
CORS_ORIGINS=*
API_KEYS=dev-api-key-123,test-key-456

# Storage configuration
STORAGE_PROVIDER=local
STORAGE_BUCKET_NAME=ohm-storage

# LLM configuration (optional)
LLM_ENABLED=false
```

### Step 3: Start Services

```bash
# Start main API service
docker-compose up -d ohm-api

# Check service status
docker-compose ps

# View logs
docker-compose logs -f ohm-api
```

### Step 4: Verify Endpoints

All demo endpoints should be accessible:

- **Health**: `http://localhost:8001/health`
- **Match**: `http://localhost:8001/v1/api/match`
- **OKH**: `http://localhost:8001/v1/api/okh`
- **OKW**: `http://localhost:8001/v1/api/okw/search`

## Verification

### Automated Verification

Run the verification script:

```bash
python -m demo.infrastructure.verify_local_deployment
```

Expected output:
```
🔍 Verifying local Docker deployment...
URL: http://localhost:8001

Health Check Results:
============================================================
Health Endpoint:     ✅ Status: 200, Latency: <10ms
Match Endpoint:      ✅ Status: 200, Latency: <5s
OKH Endpoint:        ✅ Status: 200, Latency: <500ms
OKW Endpoint:        ✅ Status: 200 or timeout (if no data)
============================================================

✅ All endpoints are accessible!
```

### Manual Verification

```bash
# Health check
curl http://localhost:8001/health

# Expected: {"status":"ok","domains":["cooking","manufacturing"],"version":"1.0.0"}

# OKH endpoint
curl "http://localhost:8001/v1/api/okh?page=1&page_size=1"

# Match endpoint (requires payload)
curl -X POST http://localhost:8001/v1/api/match \
  -H "Content-Type: application/json" \
  -d '{"okh_manifest": {"title": "Test", "version": "1.0.0"}}'
```

## Troubleshooting

### Service Won't Start

**Problem**: `docker-compose up` fails

**Solutions**:
1. Check if port 8001 is already in use:
   ```bash
   lsof -i :8001
   ```
2. Check Docker is running:
   ```bash
   docker ps
   ```
3. Review logs:
   ```bash
   docker-compose logs ohm-api
   ```

### Endpoints Not Accessible

**Problem**: `curl http://localhost:8001/health` fails

**Solutions**:
1. Verify container is running:
   ```bash
   docker-compose ps
   ```
2. Check container logs:
   ```bash
   docker-compose logs ohm-api
   ```
3. Verify port mapping:
   ```bash
   docker-compose port ohm-api 8001
   ```

### OKW Endpoint Timeout

**Problem**: OKW endpoint times out

**Solutions**:
1. This is expected if no OKW data is loaded
2. Load demo data (see "Loading Demo Data" section)
3. Check storage volume:
   ```bash
   docker volume inspect supply-graph-ai_ohm-storage
   ```

### High Latency

**Problem**: Endpoints respond slowly

**Solutions**:
1. Check system resources:
   ```bash
   docker stats ohm-api
   ```
2. Review application logs for errors
3. Consider increasing Docker resources

## Loading Demo Data

### Option 1: Using API Endpoints

Upload OKH and OKW files via API:

```bash
# Upload OKH file
curl -X POST http://localhost:8001/v1/api/okh \
  -H "Content-Type: application/json" \
  -d @path/to/okh-file.json

# Upload OKW file
curl -X POST http://localhost:8001/v1/api/okw \
  -H "Content-Type: application/json" \
  -d @path/to/okw-file.json
```

### Option 2: Direct Storage Access

If using local storage provider, copy files directly to storage volume:

```bash
# Find volume path
docker volume inspect supply-graph-ai_ohm-storage

# Copy files (example - adjust path)
docker cp path/to/okh-file.json ohm-api:/app/storage/okh/
docker cp path/to/okw-file.json ohm-api:/app/storage/okw/
```

### Option 3: Mount Local Directory

Modify `docker-compose.yml` to mount local directories:

```yaml
volumes:
  - ./storage:/app/storage
  - ./test-data:/app/test-data
```

Then copy files to `./storage/` directory.

## Monitoring

### View Logs

```bash
# Follow logs
docker-compose logs -f ohm-api

# Last 100 lines
docker-compose logs --tail=100 ohm-api
```

### Check Resource Usage

```bash
docker stats ohm-api
```

### Health Checks

The container includes a health check:

```bash
# Check health status
docker inspect ohm-api | grep -A 10 Health
```

## Additional Services

### Prometheus (Optional)

Start Prometheus for metrics:

```bash
docker-compose --profile monitoring up -d prometheus
```

Access at: `http://localhost:9090`

### CLI Service (Optional)

Run CLI commands in container:

```bash
docker-compose --profile cli run --rm ohm-cli <command>
```

## Quick Reference Checklist

### Pre-Demo Setup

- [ ] Docker and Docker Compose installed
- [ ] `.env` file configured
- [ ] Port 8001 available
- [ ] `docker-compose up -d` executed
- [ ] Health endpoint verified (`curl http://localhost:8001/health`)
- [ ] All API endpoints tested
- [ ] Demo data loaded (if needed)
- [ ] Verification script passes

### During Demo

- [ ] Monitor logs: `docker-compose logs -f ohm-api`
- [ ] Have backup URL ready: `http://localhost:8001`
- [ ] Know how to switch demo interface to local URL

### Post-Demo

- [ ] Stop services: `docker-compose down`
- [ ] Clean up volumes (if needed): `docker volume rm supply-graph-ai_ohm-storage`
- [ ] Review logs for issues

## Network Configuration

The deployment uses a bridge network (`ohm-network`). Services can communicate using service names:

- API: `http://ohm-api:8001`
- CLI: `http://ohm-api:8001` (from CLI container)

## Storage Volumes

The deployment creates persistent volumes:

- `ohm-storage`: Application data storage
- `ohm-logs`: Application logs
- `prometheus-data`: Prometheus metrics (if monitoring enabled)

To inspect volumes:

```bash
docker volume ls | grep ohm
docker volume inspect supply-graph-ai_ohm-storage
```

## Security Considerations

⚠️ **Important**: The local deployment is configured for development:

- CORS allows all origins (`CORS_ORIGINS=*`)
- Default API keys are used
- No authentication required
- Accessible only on localhost

**For production use**, modify:
- CORS origins
- API keys
- Authentication requirements
- Network binding (currently `0.0.0.0`)

## Comparison: Cloud Run vs Local

| Feature | Cloud Run | Local Docker |
|---------|-----------|--------------|
| URL | `https://supply-graph-ai-*.run.app` | `http://localhost:8001` |
| Access | Public (if configured) | Localhost only |
| Scaling | Automatic | Single instance |
| Latency | 1-7s (cold start) | <100ms (warm) |
| Data Storage | Cloud Storage | Docker volumes |
| Monitoring | Cloud Monitoring | Prometheus (optional) |
| Cost | Pay-per-use | Free (local) |

## Support

For issues or questions:

1. Check logs: `docker-compose logs ohm-api`
2. Review this runbook
3. Check `demo/infrastructure/README.md` for verification tools
4. Review `docker-compose.yml` for configuration
