# Multi-stage build: frozen dependencies from uv.lock (matches CI), non-editable install.
# Stage 1: Build dependencies and application
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Lockfile-first install for reproducible dependency resolution (same as CI).
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project --no-editable

COPY src/ ./src/
COPY config/ ./config/

RUN uv sync --frozen --no-dev --no-editable

# Required for NLP processing
RUN python -m spacy download en_core_web_md

# Stage 2: Runtime image
FROM python:3.12-slim AS runtime

ARG APP_VERSION=0.8.0
LABEL org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.title="Open Hardware Manager (OHM)" \
      org.opencontainers.image.source="https://github.com/helpfulengineering/supply-graph-ai/supply-graph-ai"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    APP_VERSION="${APP_VERSION}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY config/ ./config/
COPY deploy/docker/docker-entrypoint.sh deploy/docker/gunicorn.conf.py ./

RUN mkdir -p logs storage storage/federation temp_context temp_matching_context && \
    chmod -R 755 logs storage temp_context temp_matching_context

RUN chmod +x docker-entrypoint.sh && \
    mv docker-entrypoint.sh /usr/local/bin/

RUN groupadd -r ohm && useradd -r -g ohm ohm && \
    chown -R ohm:ohm /app && \
    chown -R ohm:ohm /opt/venv

# Entrypoint fixes named-volume ownership, then execs as ohm
USER root

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD sh -c 'curl -f http://localhost:${PORT:-8001}/health || exit 1'

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

CMD ["api"]
