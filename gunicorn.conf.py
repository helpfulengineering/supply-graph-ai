# Gunicorn configuration for Open Matching Engine
# This configuration is optimized for production deployment

import multiprocessing
import os

# Server socket
# Support PORT env var (Cloud Run) and API_PORT (backward compatibility)
# Cloud Run sets PORT=8080, so we prioritize PORT over API_PORT
port_env = os.getenv('PORT')
api_port_env = os.getenv('API_PORT')
port = port_env or api_port_env or '8001'
# Ensure port is a string for the bind address
port = str(port) if port else '8001'
bind = f"0.0.0.0:{port}"

# Debug output (will appear in Gunicorn startup logs)
print(f"[Gunicorn Config] PORT env var: {port_env}")
print(f"[Gunicorn Config] API_PORT env var: {api_port_env}")
print(f"[Gunicorn Config] Using port: {port}")
print(f"[Gunicorn Config] Binding to: {bind}")

backlog = 2048

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
# Use uvicorn workers for async FastAPI application
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'uvicorn.workers.UvicornWorker')
worker_connections = int(os.getenv('GUNICORN_WORKER_CONNECTIONS', '1000'))
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '100'))

# Timeout settings
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', '5'))

# Logging
accesslog = os.getenv('GUNICORN_ACCESS_LOG', '-')
errorlog = os.getenv('GUNICORN_ERROR_LOG', '-')
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
access_log_format = os.getenv('GUNICORN_ACCESS_LOG_FORMAT', 
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s')

# Process naming
proc_name = 'open-matching-engine'

# Server mechanics
daemon = False
pidfile = '/tmp/gunicorn.pid'
# Note: user/group are set in Dockerfile (USER ome), so we don't need to set them here
# If we're already running as the correct user, Gunicorn will skip privilege dropping
# user = 'ome'  # Commented out - already running as ome user in container
# group = 'ome'  # Commented out - already running as ome user in container
tmp_upload_dir = None

# SSL (if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Preload application for better performance
preload_app = True

# Additional worker settings
keepalive_timeout = int(os.getenv('GUNICORN_KEEPALIVE_TIMEOUT', '5'))
