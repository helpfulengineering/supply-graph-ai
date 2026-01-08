# Prometheus Setup for Local Testing

This guide explains how to set up Prometheus to scrape metrics from the supply-graph-ai service.

## Prerequisites

- Docker and Docker Compose installed
- Docker Desktop file sharing permissions configured (if on macOS/Windows)

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. **Ensure Docker Desktop file sharing is enabled** (macOS/Windows):
   - Docker Desktop → Settings → Resources → File Sharing
   - Add your project directory if not already included

2. **Start the services**:
   ```bash
   docker-compose --profile monitoring up -d ohm-api prometheus
   ```

3. **Access Prometheus UI**:
   - Open http://localhost:9090 in your browser
   - Navigate to Status → Targets to verify the scrape target is UP
   - Use the Graph tab to query metrics (e.g., `http_requests_total`)

### Option 2: Manual Prometheus Setup

If you encounter Docker volume mount permission issues:

1. **Start the API container**:
   ```bash
   docker-compose up -d ohm-api
   ```

2. **Run Prometheus with inline config**:
   ```bash
   docker run -d \
     --name ohm-prometheus \
     --network supply-graph-ai_ohm-network \
     -p 9090:9090 \
     prom/prometheus:latest \
     --config.file=/dev/stdin <<EOF
   global:
     scrape_interval: 15s
   scrape_configs:
     - job_name: 'supply-graph-ai'
       static_configs:
         - targets: ['ohm-api:8001']
           labels:
             service: 'supply-graph-ai'
   EOF
   ```

   Note: This approach doesn't persist the config, but works for quick testing.

## Configuration

The Prometheus configuration is located at `config/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'supply-graph-ai'
    scrape_interval: 15s
    metrics_path: '/v1/api/utility/metrics'
    params:
      format: ['prometheus']
    static_configs:
      - targets: ['ohm-api:8001']
        labels:
          service: 'supply-graph-ai'
          instance: 'local'
```

## Verifying Metrics Collection

### Check Target Status

```bash
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="supply-graph-ai")'
```

Expected output should show `"health": "up"`.

### Query Metrics

```bash
# Total requests
curl 'http://localhost:9090/api/v1/query?query=http_requests_total'

# Requests by endpoint
curl 'http://localhost:9090/api/v1/query?query=http_requests_total{path="/health"}'

# Request duration
curl 'http://localhost:9090/api/v1/query?query=http_request_duration_seconds'
```

### Generate Some Traffic

To see metrics increase, make some API requests:

```bash
# Make several requests
for i in {1..10}; do
  curl http://localhost:8001/health
  curl http://localhost:8001/v1/api/utility/domains
done

# Then query Prometheus again
curl 'http://localhost:9090/api/v1/query?query=http_requests_total'
```

## Troubleshooting

### Docker Volume Mount Permission Issues (macOS/Windows)

**Error**: `error while creating mount source path: operation not permitted`

**Solution**:
1. Open Docker Desktop
2. Go to Settings → Resources → File Sharing
3. Add your project directory (e.g., `/Users/username/Documents/workspace/personal/supply-graph-ai`)
4. Click "Apply & Restart"
5. Try again

### Prometheus Target Shows as DOWN

1. **Check if API is running**:
   ```bash
   docker ps | grep ohm-api
   curl http://localhost:8001/health
   ```

2. **Check Prometheus can reach the API**:
   ```bash
   docker exec ohm-prometheus wget -qO- http://ohm-api:8001/v1/api/utility/metrics?format=prometheus | head -10
   ```

3. **Check Prometheus logs**:
   ```bash
   docker logs ome-prometheus
   ```

### No Metrics Appearing

1. **Verify metrics endpoint works**:
   ```bash
   curl 'http://localhost:8001/v1/api/utility/metrics?format=prometheus'
   ```

2. **Generate some traffic** to the API (metrics only appear after requests are made)

3. **Check scrape interval** - Prometheus scrapes every 15 seconds by default

## Example Queries

Once Prometheus is collecting metrics, try these queries in the Prometheus UI:

- **Total requests**: `http_requests_total`
- **Requests by method**: `http_requests_total{method="GET"}`
- **Requests by endpoint**: `http_requests_total{path="/health"}`
- **Error rate**: `rate(http_requests_failed_total[5m])`
- **Request duration (p95)**: `http_request_duration_seconds{quantile="0.95"}`

## Cleanup

To stop and remove the containers:

```bash
docker-compose --profile monitoring down
```

To also remove the Prometheus data volume:

```bash
docker-compose --profile monitoring down -v
```

