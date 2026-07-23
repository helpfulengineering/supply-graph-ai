#!/usr/bin/env bash
# Provision ephemeral Azure federation peers (two-pass apply to wire MANUAL_PEERS).
#
# Prerequisites: az login, terraform >= 1.5, Docker Hub image pullable.
#
# Usage:
#   ./deploy/terraform/azure/scripts/up.sh
#   eval "$(terraform -chdir=deploy/terraform/azure output -raw matrix_env)"
#   ./scripts/federation_matrix.sh
#   RUN_ROLE_CASES=1 ./scripts/federation_matrix.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TF_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$TF_DIR"

TFVARS="${TFVARS:-environments/federation-ephemeral.tfvars}"
if [[ ! -f "$TFVARS" && -f environments/federation-ephemeral.tfvars.example ]]; then
  cp environments/federation-ephemeral.tfvars.example "$TFVARS"
  echo "[fed-azure-up] created $TFVARS from example"
fi

log() { echo "[fed-azure-up] $*"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    log "ERROR: $1 not found"
    exit 1
  }
}

require_cmd terraform
require_cmd az
require_cmd jq

if ! az account show >/dev/null 2>&1; then
  log "ERROR: not logged in — run: az login"
  exit 1
fi

log "terraform init"
terraform init -upgrade

EXTRA=()
if [[ -f "$TFVARS" ]]; then
  EXTRA=(-var-file="$TFVARS")
  log "using tfvars: $TFVARS"
fi

log "pass 1: create resource group + nodes (empty MANUAL_PEERS)"
terraform apply -auto-approve "${EXTRA[@]}" \
  -var '_manual_peers_a=' \
  -var '_manual_peers_b=' \
  -var '_manual_peers_edge=' \
  -var '_manual_peers_relay='

PEER_A="$(terraform output -raw peer_a_url)"
PEER_B="$(terraform output -raw peer_b_url)"
EDGE="$(terraform output -raw edge_url 2>/dev/null || true)"
RELAY="$(terraform output -raw relay_url 2>/dev/null || true)"

log "pass 2: wire MANUAL_PEERS to public FQDNs"
PEERS_A="$PEER_B"
PEERS_B="$PEER_A"
[[ -n "$RELAY" && "$RELAY" != "null" ]] && PEERS_A="${PEERS_A},${RELAY}" && PEERS_B="${PEERS_B},${RELAY}"
PEERS_EDGE="$PEER_A"
PEERS_RELAY="${PEER_A},${PEER_B}"

terraform apply -auto-approve "${EXTRA[@]}" \
  -var "_manual_peers_a=${PEERS_A}" \
  -var "_manual_peers_b=${PEERS_B}" \
  -var "_manual_peers_edge=${PEERS_EDGE}" \
  -var "_manual_peers_relay=${PEERS_RELAY}"

log "waiting for health (up to ~5 min per peer)..."
for url in "$PEER_A" "$PEER_B"; do
  ok=0
  for i in $(seq 1 60); do
    if curl -sf --max-time 10 "${url}/health/liveness" >/dev/null 2>&1 \
      || curl -sf --max-time 10 "${url}/health" >/dev/null 2>&1; then
      log "healthy: $url"
      ok=1
      break
    fi
    if (( i % 6 == 0 )); then
      log "still waiting on ${url} (attempt ${i}/60)…"
    fi
    sleep 5
  done
  if [[ "$ok" -ne 1 ]]; then
    log "WARNING: $url not healthy yet — continue anyway"
    log "  debug: az containerapp logs show -g $(terraform output -raw resource_group) -n <app> --type console --tail 50"
  fi
done

log "done. Export env and run the matrix:"
echo
terraform output -raw matrix_env
echo
log "Optional seed: ./scripts/federation_seed_azure.sh"
log "Teardown: ./deploy/terraform/azure/scripts/down.sh"
log "Cost: destroy when idle — min_replicas=0 in tfvars reduces idle spend before destroy."
