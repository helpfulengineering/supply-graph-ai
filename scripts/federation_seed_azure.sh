#!/usr/bin/env bash
# Seed divergent OKH catalogs on Peer A and Peer B (after terraform up).
#
# Requires: PEER_A_URL, PEER_B_URL, API_KEY_A, API_KEY_B
# Optional: SEED_FILE (default test-data/federation/e2e-seed-manifest.json)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SEED_FILE="${SEED_FILE:-test-data/federation/e2e-seed-manifest.json}"
SUFFIX="${UNIQUE_SUFFIX:-$(uuidgen | tr '[:upper:]' '[:lower:]')}"
SHORT="${SUFFIX:0:8}"

: "${PEER_A_URL:?set PEER_A_URL}"
: "${PEER_B_URL:?set PEER_B_URL}"
: "${API_KEY_A:?set API_KEY_A}"
: "${API_KEY_B:?set API_KEY_B}"

log() { echo "[federation-seed] $*"; }

create_and_promote() {
  local base="$1"
  local key="$2"
  local title="$3"
  local id
  id="$(uuidgen | tr '[:upper:]' '[:lower:]')"
  local manifest
  manifest="$(jq --arg id "$id" --arg title "$title" \
    '.id = $id | .title = $title' "$SEED_FILE")"
  local body
  body="$(curl -sS -X POST "${base}/v1/api/okh/create" \
    -H "Authorization: Bearer ${key}" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --argjson content "$manifest" '{content: $content}')")"
  echo "$body" | jq -e '.success == true' >/dev/null
  curl -sS -X PUT "${base}/v1/api/okh/${id}/visibility" \
    -H "Authorization: Bearer ${key}" \
    -H "Content-Type: application/json" \
    -d '{"visibility":"public"}' | jq -e '.visibility == "public"' >/dev/null
  log "created+public on ${base}: ${title} (${id})"
}

create_and_promote "$PEER_A_URL" "$API_KEY_A" "Seed A-only Widget ${SHORT}"
create_and_promote "$PEER_A_URL" "$API_KEY_A" "Seed A Shared Gadget ${SHORT}"
create_and_promote "$PEER_B_URL" "$API_KEY_B" "Seed B-only Fixture ${SHORT}"

log "done — catalogs are intentionally asymmetric before follow/sync"
