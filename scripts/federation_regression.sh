#!/usr/bin/env bash
# Pre-merge regression checks for the federation branch.
#
# Verifies:
#   1. All federation unit/contract tests
#   2. Federation-off behavior (core /health unaffected, /federation/* 404)
#   3. Main-branch parity subset (tests present on main today)
#
# Usage:
#   ./scripts/federation_regression.sh
#   SKIP_E2E=1 ./scripts/federation_regression.sh   # skip docker e2e

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

log() { echo "[federation-regression] $*"; }

run_pytest() {
  local label="$1"
  shift
  log "Running: $label"
  uv run python -m pytest "$@" -q --tb=short
  log "PASS: $label"
}

run_pytest "federation module tests" tests/federation/

run_pytest "federation disabled regression" tests/federation/test_regression_disabled.py

run_pytest "main-branch parity subset" \
  tests/api/test_scaffold_cleanup_endpoint.py \
  tests/cli/test_scaffold_cleanup_cli.py \
  tests/performance/test_supply_tree_performance.py \
  tests/services/test_cleanup_service.py

if [[ "${SKIP_E2E:-}" != "1" ]] && command -v docker >/dev/null 2>&1; then
  if curl -sf http://localhost:8001/health >/dev/null 2>&1 \
     && curl -sf http://localhost:8002/health >/dev/null 2>&1; then
    log "Two-node stack detected — running federation_e2e.sh"
    ./scripts/federation_e2e.sh
    log "PASS: federation E2E"
  else
    log "Skipping E2E (start with: docker compose -f docker-compose.federation.yml up -d)"
  fi
fi

log "All regression checks passed."
