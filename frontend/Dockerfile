# syntax=docker/dockerfile:1

# ---- Build stage: compile the SPA to static assets ----
FROM node:22-alpine AS build
WORKDIR /app

# Install deps against the committed lockfile (reproducible, matches CI).
COPY package.json package-lock.json ./
RUN npm ci

# Build (tsc -b && vite build) → /app/dist
COPY . .
RUN npm run build

# ---- Runtime stage: nginx serving the SPA + proxying /v1 to the backend ----
FROM nginx:1.27-alpine AS runtime

# The base image runs envsubst over templates at startup, rendering this into
# /etc/nginx/conf.d/default.conf with the host-specific values below.
COPY deploy/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

# Host-specific config — injected at deploy time from the centralized config
# surface (config/environments/<env>.toml [frontend]); NOT baked into the image.
# API_UPSTREAM_URL has no default on purpose: an unset value fails nginx startup
# loudly rather than silently proxying nowhere.
ENV API_UPSTREAM_URL="" \
    PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- "http://localhost:${PORT}/healthz" >/dev/null 2>&1 || exit 1

# Base image ENTRYPOINT renders templates (envsubst) then starts nginx.
