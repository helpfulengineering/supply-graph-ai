# ADR: Federation MVP (LAN Peer Sync)

## Status

Accepted

## Date

2026-05-17

## Context

OHM Phase 5 ([roadmap](../development/roadmap.md)) requires federated OKH design synchronization. Prior art ([notes/federation-prior-art-and-recommendations.md](../../notes/federation-prior-art-and-recommendations.md)) recommends a three-tier stack (physical mesh → LAN → internet). We need a minimal, testable slice before relay/registry, IPFS, or ActivityPub.

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
| Default | `OHM_FEDERATION_ENABLED=false` — centralized OHM unchanged |

### Deferred (explicit non-goals for MVP)

- LoRa / Meshtastic, IPFS Kubo, libp2p DHT, ActivityPub, CouchDB replication
- Relay mailbox, registry directory, package artifact sync
- Web-of-trust scoring, malware sandboxing, global bootstrap DNS

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

## References

- Implementation plan: `.cursor/plans/ohm_federation_mvp_e439161b.plan.md`
- W3C DID Core; `did:key` method
- OAI-PMH verb pattern (Identify, ListRecords, GetRecord) for HTTP catalog shape
