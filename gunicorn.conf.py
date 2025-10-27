# Gunicorn configuration for Open Matching Engine
# This configuration is optimized for production deployment

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('API_PORT', '8001')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'gevent')
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
user = 'ome'
group = 'ome'
tmp_upload_dir = None

# SSL (if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Preload application for better performance
preload_app = True

# Additional worker settings
keepalive_timeout = int(os.getenv('GUNICORN_KEEPALIVE_TIMEOUT', '5'))
