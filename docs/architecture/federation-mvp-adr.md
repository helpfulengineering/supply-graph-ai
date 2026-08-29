# ADR: Federation MVP (LAN Peer Sync)

## Status

Accepted

## Date

2026-05-17

## Context

OHM requires federated OKH design synchronization.

A prior-art survey (OAI-PMH, Secure Scuttlebutt, IPFS, ActivityPub, CouchDB
replication, Kademlia, mDNS/Zeroconf, disaster mesh networking, DIDs) pointed at
a **three-tier discovery architecture**, each tier independent of the ones above
it so the system degrades rather than fails:

| Tier | Transport | Propagates |
|---|---|---|
| 1 — physical mesh | LoRa / Serval | content hashes, node names, summaries |
| 2 — local LAN | mDNS / Zeroconf | full manifests, design metadata, replication sync |
| 3 — internet | DHT + ActivityPub | full manifests and files, globally searchable |

A node in a total blackout still propagates design hashes to neighbours over
Tier 1; when WiFi returns, Tier 2 syncs manifests; when the internet returns,
Tier 3 makes them globally discoverable.

This ADR takes a minimal, testable slice of that before committing to relay,
registry, IPFS, or ActivityPub.

*The survey lives in the maintainers' working notes, which are not tracked in
this repository — its conclusions are summarised above so this decision can be
read and challenged without them.*

## Decision

Implement **Tier 2 (LAN) peer federation** in `src/core/federation/`:

| Concern | MVP choice |
|---|---|
| Node role | `peer` only (`edge` / `relay` / `registry` stubbed in `node_role.py`) |
| Identity | `did:key` (Ed25519), persisted under `OHM_FEDERATION_DATA_DIR` |
| Content ID | `sha256:` + hex digest of canonical manifest JSON |
| Sync | Anti-entropy via Merkle root + HTTP (`/v1/api/federation/*`) |
| Discovery | mDNS `_ohm._tcp` (best-effort) + `OHM_FEDERATION_MANUAL_PEERS` |
| Trust | Explicit `follow` allowlist; verify signatures on ingest |
| Conflict | First-write-wins: skip `already_present` (same hash/id) or `id_conflict` (same id, divergent content); no LWW/CRDT yet |
| Default | `OHM_FEDERATION_ENABLED=false` — centralized OHM unchanged |

### Deferred (explicit non-goals for MVP)

- LoRa / Meshtastic, IPFS Kubo, libp2p DHT, ActivityPub, CouchDB replication
- Relay mailbox, registry directory
- Web-of-trust scoring, malware sandboxing, global bootstrap DNS

### Package artifacts (post-MVP channel)

OKH catalog records may carry an optional **package pointer** (`bundle_hash`,
size, filename) outside the design content hash. Bytes move on a separate
**HTTP CAS** channel (`GET /federation/packages/blobs/{bundle_hash}`), follow-gated
via `X-OHM-Peer-DID`, on-demand only (not during `sync/run`). Fetch-first with
rebuild-from-OKH-URLs fallback. World-readable packages, eager/pin-driven pull,
and Relay-as-archive are later.

### OKW catalog (separate Merkle root)

OKW facilities sync via a **separate** catalog from OKH. Coarse visibility
(`private` / `followers` / `public`) gates export; **disclosure profiles** redact
field groups (`identity`, `location`, `equipment`, `operations`, `supply`) per
audience. Default is fail-closed (identity only). Content hash and signatures
cover the redacted projection. Ingest stamps private locally.

### Post-MVP (approved direction)

- **v0.2**: `edge` (outbound-only), `relay`, `registry`; deploy relay/registry on **GCP Cloud Run + Firestore**
- **Dev infra**: Docker Compose for MVP; hybrid Compose + Cloud Run for v0.2
- **GKE**: deferred until relay HA required

## Consequences

### Positive

- Validates catalog format, signing, and sync without NAT/TLS/registry complexity
- Same HTTP protocol works for manual internet peer URLs later
- `PeerSource` abstraction allows relay/registry plugins without rewriting sync

### Negative

- mDNS unreliable in Docker bridge networks — Compose uses `MANUAL_PEERS`
- No global discovery until v0.2 registry

## Enabling federation in Docker

See also: [federation-infra.md](../ops/federation-infra.md) for the two-node Compose stack and E2E script.

`OHM_FEDERATION_*` variables must be present in the **API server process** (container), not only in the shell used for `curl`.

1. Add to `.env` (loaded by `docker-compose.yml`):

   ```bash
   OHM_FEDERATION_ENABLED=true
   OHM_FEDERATION_DATA_DIR=/app/storage/federation
   ```

   See [.env.federation.example](../../.env.federation.example).

2. Recreate the container (rebuild alone is not enough):

   ```bash
   docker compose up --build -d ohm-api
   ```

3. Confirm startup logs include `Federation enabled` and a DID.

## References

- Implementation plan: `.cursor/plans/ohm_federation_mvp_e439161b.plan.md`
- W3C DID Core; `did:key` method
- OAI-PMH verb pattern (Identify, ListRecords, GetRecord) for HTTP catalog shape
