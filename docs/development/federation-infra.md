# Federation infrastructure (MVP)

This guide covers running **two federated OHM peers** locally for development and smoke testing. For protocol decisions see [federation-mvp-adr.md](../architecture/federation-mvp-adr.md).

## Quick start (Docker Compose)

```bash
# Start two peers on ports 8001 (A) and 8002 (B)
docker compose -f docker-compose.federation.yml up --build -d

# Run end-to-end sync test
chmod +x scripts/federation_e2e.sh
./scripts/federation_e2e.sh
```

The E2E script:

1. Seeds a unique OKH manifest on **Peer A**
2. Reads Peer A's DID from `/v1/api/federation/identify`
3. **Follows** Peer A from Peer B
4. Runs **anti-entropy sync** (`POST /sync/run`)
5. Asserts the manifest appears in Peer B's catalog

## Topology

```text
┌─────────────────┐         Compose DNS          ┌─────────────────┐
│  ohm-peer-a     │ ◄──── MANUAL_PEERS ────────► │  ohm-peer-b     │
│  localhost:8001 │                              │  localhost:8002 │
│  volume: a      │                              │  volume: b      │
└─────────────────┘                              └─────────────────┘
```

Each peer has:

- Separate object storage volume (`ohm-storage-a` / `ohm-storage-b`)
- Separate federation state under `/app/storage/federation` (identity, peers, follows)
- Federation enabled via container environment (not host shell exports)

## Configuration

Copy [.env.federation.example](../../.env.federation.example) into `.env` or set variables in `docker-compose.federation.yml`.

| Variable | Purpose |
|---|---|
| `OHM_FEDERATION_ENABLED` | Master switch (`true` for federation stack) |
| `OHM_FEDERATION_DATA_DIR` | Identity + peer/follow state (use `/app/storage/federation` in containers) |
| `OHM_FEDERATION_MANUAL_PEERS` | Comma-separated peer base URLs (required in Compose; see mDNS note below) |
| `OHM_FEDERATION_MDNS_ENABLED` | LAN discovery via `_ohm._tcp` (default `true`; set `false` in Compose) |
| `OHM_FEDERATION_SYNC_INTERVAL_SEC` | Background sync interval for followed peers |
| `OHM_FEDERATION_SYNC_RATE_LIMIT_PER_MIN` | Per-peer digest/record rate limit |

## mDNS limitations

mDNS (`_ohm._tcp.local.`) works on real WiFi LANs but is **unreliable inside Docker bridge networks**. For Compose and CI:

- Set `OHM_FEDERATION_MDNS_ENABLED=false`
- Use `OHM_FEDERATION_MANUAL_PEERS=http://<compose-service-name>:8001`

On a physical LAN (no Docker), mDNS can supplement manual peers.

## API endpoints

All routes are under `/v1/api/federation/` when federation is enabled.

| Endpoint | Description |
|---|---|
| `GET /identify` | Node DID, catalog summary |
| `GET /status` | Dashboard status + sync metrics |
| `GET /catalog` | Signed catalog records |
| `GET /records/{content_hash}` | Full signed manifest |
| `POST /sync/digest` | Anti-entropy hash exchange |
| `POST /sync/run` | Pull missing records from followed peers |
| `POST /peers/{did}/follow` | Allow ingest from peer |

## Trust model

- Peers discovered via mDNS or manual URLs start **unfollowed**
- Sync only **ingests** manifests from **followed** DIDs
- All records must pass signature verification and OKH validation

## Sharing / visibility

What leaves your node is an **opt-in** local policy (federated-identity Slice 4).
New OKH/OKW creates default to `private` and never appear in `GET /catalog`.
Promote a record to share it with peers that sync from you:

| Visibility | In `/catalog`? |
|---|---|
| `private` | No (default on create) |
| `followers` | Yes |
| `public` | Yes |

```bash
ohm okh visibility set <manifest_id> public
ohm okh visibility show <manifest_id>
```

Visibility is **local** (not carried on the catalog record). A peer that ingests a
design decides independently whether to re-share it. See
[Identity Model — Record visibility](../architecture/identity-model.md).

## CLI

```bash
ohm federation status
ohm federation peers --discover
ohm federation follow did:key:...
ohm federation sync --peer http://localhost:8001
```

## Single-node development

For one container (`docker compose up ohm-api`), enable federation in `.env`:

```bash
OHM_FEDERATION_ENABLED=true
OHM_FEDERATION_DATA_DIR=/app/storage/federation
```

Recreate the container after changing federation env vars:

```bash
docker compose up --build -d ohm-api
```

## Post-MVP (v0.2)

Relay and registry nodes are planned for Cloud Run + Firestore to support NAT'd **edge** nodes. The LAN HTTP sync protocol remains the same; only discovery and connectivity layers change.
