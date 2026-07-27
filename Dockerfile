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

# The spaCy model (en_core_web_md) is a pinned dependency in pyproject.toml /
# uv.lock, so the syncs above already installed it into /opt/venv. No separate
# `spacy download` step — that installed it untracked, and uv's exact sync then
# removed it on subsequent syncs.

# Stage 2: Runtime image
FROM python:3.12-slim AS runtime

ARG APP_VERSION=0.8.0
# The commit this image was built from. A version alone cannot identify a build:
# two images published under the same release tag report the same version, so a
# deploy that silently fails to roll over looks healthy. /health reports this so
# a deploy can assert it is running the image it just pushed.
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.title="Open Hardware Manager (OHM)" \
      org.opencontainers.image.source="https://github.com/helpfulengineering/supply-graph-ai/supply-graph-ai"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    APP_VERSION="${APP_VERSION}" \
    GIT_SHA="${GIT_SHA}"

# curl: container healthcheck.
# git:  the generation pipeline's clone path (`clone=true`) shells out to
#       `git clone --depth 1 --single-branch`. Without it the clone fails
#       instantly and generation falls back to fetching every file over the GitHub
#       Contents API — one HTTP round trip per file, which cannot finish a large
#       repository inside the proxy timeout.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
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
