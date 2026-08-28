#!/bin/sh
# Container entry point. nginx used to fail startup loudly when the upstream
# was unset (envsubst rendered an invalid proxy_pass); preserve that contract
# for the node server rather than letting /v1 requests 502 silently.
set -eu

if [ -z "${API_UPSTREAM_URL:-}" ]; then
  echo "FATAL: API_UPSTREAM_URL is not set — refusing to start." >&2
  echo "Set it from config/environments/<env>.toml [frontend] api_upstream_url." >&2
  exit 1
fi

exec node server.js
