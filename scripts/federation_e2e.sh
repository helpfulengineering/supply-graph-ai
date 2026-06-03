#!/usr/bin/env bash
# End-to-end federation smoke test: seed manifest on peer A, sync to peer B.
#
# Prerequisites:
#   docker compose -f docker-compose.federation.yml up --build -d
#
# Usage:
#   ./scripts/federation_e2e.sh
#   PEER_A_URL=http://localhost:8001 PEER_B_URL=http://localhost:8002 ./scripts/federation_e2e.sh

set -euo pipefail

PEER_A_URL="${PEER_A_URL:-http://localhost:8001}"
PEER_B_URL="${PEER_B_URL:-http://localhost:8002}"
SEED_FILE="${SEED_FILE:-test-data/federation/e2e-seed-manifest.json}"
UNIQUE_SUFFIX="${UNIQUE_SUFFIX:-$(uuidgen | tr '[:upper:]' '[:lower:]')}"
TITLE="Federation E2E Seed ${UNIQUE_SUFFIX:0:8}"

log() {
  echo "[federation-e2e] $*"
}

wait_healthy() {
  local base_url="$1"
  local name="$2"
  local attempts=30
  local i=1
  while [[ "$i" -le "$attempts" ]]; do
    if curl -sf "${base_url}/health" >/dev/null; then
      log "${name} is healthy (${base_url})"
      return 0
    fi
    sleep 2
    i=$((i + 1))
  done
  log "ERROR: ${name} did not become healthy at ${base_url}"
  return 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    log "ERROR: required command not found: $1"
    exit 1
  }
}

require_cmd curl
require_cmd jq

if [[ ! -f "$SEED_FILE" ]]; then
  log "ERROR: seed manifest not found: $SEED_FILE"
  exit 1
fi

wait_healthy "$PEER_A_URL" "Peer A"
wait_healthy "$PEER_B_URL" "Peer B"

MANIFEST_ID="$(uuidgen | tr '[:upper:]' '[:lower:]')"
MANIFEST_JSON="$(jq \
  --arg id "$MANIFEST_ID" \
  --arg title "$TITLE" \
  '.id = $id | .title = $title' \
  "$SEED_FILE")"

log "Creating manifest on Peer A (id=${MANIFEST_ID})"
CREATE_RESP="$(curl -sf -X POST "${PEER_A_URL}/v1/api/okh/create" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --argjson content "$MANIFEST_JSON" '{content: $content}')")"
echo "$CREATE_RESP" | jq -e '.success == true' >/dev/null

PEER_A_DID="$(curl -sf "${PEER_A_URL}/v1/api/federation/identify" | jq -r '.did')"
log "Peer A DID: ${PEER_A_DID}"

log "Following Peer A from Peer B"
curl -sf -X POST "${PEER_B_URL}/v1/api/federation/peers/${PEER_A_DID}/follow" >/dev/null

log "Running sync on Peer B"
SYNC_RESP="$(curl -sf -X POST "${PEER_B_URL}/v1/api/federation/sync/run?peer_url=${PEER_A_URL}")"
echo "$SYNC_RESP" | jq .

PULLED="$(echo "$SYNC_RESP" | jq -r '.total_pulled // 0')"
if [[ "$PULLED" -lt 1 ]]; then
  log "ERROR: expected at least 1 record pulled, got ${PULLED}"
  echo "$SYNC_RESP" | jq .
  exit 1
fi

log "Verifying manifest title on Peer B catalog"
FOUND="$(curl -sf "${PEER_B_URL}/v1/api/federation/catalog" \
  | jq -r --arg title "$TITLE" '[.records[] | select(.title == $title)] | length')"
if [[ "$FOUND" -lt 1 ]]; then
  log "ERROR: catalog on Peer B does not contain title '${TITLE}'"
  exit 1
fi

log "SUCCESS: federation E2E passed (pulled=${PULLED}, title='${TITLE}')"
