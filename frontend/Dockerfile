# syntax=docker/dockerfile:1

# ---- Build stage: compile the Next.js app to a standalone server ----
#
# Pinned to BUILDPLATFORM so this stage runs once, natively, instead of once per
# target architecture under QEMU. `next build` emits portable JavaScript, so one
# build serves both architectures; only the runtime stage below has to vary, and
# it does nothing but COPY.
#
# This is not a micro-optimisation. Emulated `npm ci` is syscall-bound
# single-threaded work and it does not finish in a useful time: the v0.11.0
# release sat on it for 52 minutes and was cancelled, against 7 minutes for the
# Vite image this replaced. Dropping the emulated pass is the difference between
# a release that ships and one that does not.
FROM --platform=$BUILDPLATFORM node:22-alpine AS build
WORKDIR /app

# Install deps against the committed lockfile (reproducible, matches CI).
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Build identity, baked in so a deploy can prove which image is actually
# serving. A version string cannot do this: republishing a release tag yields a
# new image reporting the same version, so a deploy that silently fails to roll
# over still passes a version check. Static file rather than a runtime env var —
# it has to describe the IMAGE, not the container's environment. Written before
# `next build` so the standalone output carries it.
ARG GIT_SHA=unknown
RUN mkdir -p public && printf '{"build":"%s"}\n' "${GIT_SHA}" > public/build-info.json

# next build → .next/standalone (server) + .next/static (assets)
RUN npm run build

# ---- Runtime stage: the standalone node server (replaces nginx) ----
# The server owns every contract nginx used to: /v1 proxy (app/v1 route
# handler), /docs static tree (app/docs route handler), /healthz, and
# /build-info.json + /_next/static via the bundled asset server.
FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production

COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public

# Documentation site, served at /docs by the docs route handler. Built by
# `make docs-site` (mkdocs writes straight into this context via site_dir), so
# it must be built BEFORE the image. CI does that in the publish-frontend job;
# a stale or empty docs-dist ships an empty docs section, which the post-deploy
# smoke check is there to catch.
COPY docs-dist ./docs-dist

ARG GIT_SHA=unknown
LABEL org.opencontainers.image.revision="${GIT_SHA}"

# Host-specific config — injected at deploy time from the centralized config
# surface (config/environments/<env>.toml [frontend]); NOT baked into the image.
# API_UPSTREAM_URL has no default on purpose: entry.sh refuses to start on an
# unset value, failing loudly rather than silently proxying nowhere (the same
# behaviour nginx's envsubst startup gave the previous image).
ENV API_UPSTREAM_URL="" \
    DOCS_ROOT=/app/docs-dist \
    HOSTNAME=0.0.0.0 \
    PORT=8080

COPY entry.sh ./entry.sh
RUN chmod +x entry.sh

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- "http://localhost:${PORT}/healthz" >/dev/null 2>&1 || exit 1

CMD ["./entry.sh"]
