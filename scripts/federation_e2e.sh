#!/usr/bin/env bash
# Thin wrapper — prefer scripts/federation_matrix.sh for the full suite.
#
# Prerequisites:
#   docker compose -f docker-compose.federation.yml up --build -d
#
# Usage:
#   ./scripts/federation_e2e.sh
#   PEER_A_URL=http://localhost:8001 PEER_B_URL=http://localhost:8002 ./scripts/federation_e2e.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/scripts/federation_matrix.sh" "$@"
