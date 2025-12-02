# Minimal Dockerfile for Prometheus on Cloud Run
# Uses official Prometheus image and generates config from environment variables

FROM prom/prometheus:latest

# Copy the entrypoint script with execute permissions
# Using --chmod to set permissions during copy (avoids permission issues)
COPY --chmod=755 entrypoint.sh /prometheus-entrypoint.sh

ENTRYPOINT ["/prometheus-entrypoint.sh"]
