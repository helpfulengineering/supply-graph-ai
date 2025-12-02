#!/bin/sh
# Entrypoint script for Prometheus on Cloud Run
# Generates Prometheus config from environment variables and starts Prometheus

# Get configuration from environment variables
PORT=${PORT:-9090}
TARGET_SERVICE_URL=${TARGET_SERVICE_URL:-supply-graph-ai-1085931013579.us-west1.run.app}
SCRAPE_INTERVAL=${SCRAPE_INTERVAL:-15s}

# Generate Prometheus configuration file
cat > /tmp/prometheus.yml <<EOF
global:
  scrape_interval: ${SCRAPE_INTERVAL}
  evaluation_interval: ${SCRAPE_INTERVAL}
  external_labels:
    environment: 'cloud-run'
    project: 'supply-graph-ai'

scrape_configs:
  - job_name: 'supply-graph-ai-cloud-run'
    scrape_interval: ${SCRAPE_INTERVAL}
    metrics_path: '/v1/api/utility/metrics'
    params:
      format: ['prometheus']
    scheme: 'https'
    static_configs:
      - targets: ['${TARGET_SERVICE_URL}']
        labels:
          service: 'supply-graph-ai'
          environment: 'cloud-run'
          region: 'us-west1'
EOF

# Start Prometheus with the generated config
exec /bin/prometheus \
  --config.file=/tmp/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.console.libraries=/usr/share/prometheus/console_libraries \
  --web.console.templates=/usr/share/prometheus/consoles \
  --web.listen-address=0.0.0.0:${PORT} \
  --web.enable-lifecycle

