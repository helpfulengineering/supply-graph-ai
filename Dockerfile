# Multi-stage build for smaller final image
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies to a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set work directory
WORKDIR /app

# Copy only necessary application files (respects .dockerignore)
# Copy package configuration first (for pip install)
COPY pyproject.toml ./
COPY requirements.txt ./

# Copy source code
COPY src/ ./src/

# Copy configuration files
COPY config/ ./config/

# Copy entrypoint and other necessary files
COPY docker-entrypoint.sh gunicorn.conf.py run.py ./

# Install the package in editable mode (creates 'ohm' command)
RUN pip install --no-cache-dir -e .

# Download spaCy model (required for NLP processing)
RUN python -m spacy download en_core_web_md

# Create necessary directories with proper permissions
RUN mkdir -p logs storage temp_context temp_matching_context && \
    chmod -R 755 logs storage temp_context temp_matching_context

# Create entrypoint script executable
RUN chmod +x docker-entrypoint.sh && \
    mv docker-entrypoint.sh /usr/local/bin/

# Create a non-root user for security
RUN groupadd -r ohm && useradd -r -g ohm ohm && \
    chown -R ohm:ohm /app && \
    chown -R ohm:ohm /opt/venv

USER ohm

# Expose port for API server (Cloud Run will override with PORT env var)
EXPOSE 8001

# Health check
# Use shell form to allow variable expansion for PORT
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD sh -c 'curl -f http://localhost:${PORT:-8001}/health || exit 1'

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command (can be overridden)
CMD ["api"]
