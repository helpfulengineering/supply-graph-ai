# Federation infrastructure (MVP)

This guide covers running **federated OHM peers** locally for development and
validation. For protocol decisions see [federation-mvp-adr.md](../architecture/federation-mvp-adr.md).
For ephemeral multi-region Azure peers see [`deploy/terraform/azure/README.md`](../../deploy/terraform/azure/README.md)
and Azure bring-up notes in [`deploy/terraform/azure/README.md`](../../deploy/terraform/azure/README.md).

## Quick start (Docker Compose)

```bash
# Start two peers on ports 8001 (A) and 8002 (B)
docker compose -f docker-compose.federation.yml up --build -d

# Full validation matrix (visibility, follow/unfollow, sync, provenance, …)
chmod +x scripts/federation_matrix.sh
./scripts/federation_matrix.sh

# Optional: background-sync wait + role stubs
docker compose -f docker-compose.federation.yml --profile roles up --build -d
RUN_SLOW_CASES=1 RUN_ROLE_CASES=1 \
  EDGE_URL=http://localhost:8003 RELAY_URL=http://localhost:8004 \
  ./scripts/federation_matrix.sh
```

`scripts/federation_e2e.sh` is a thin wrapper around the matrix.

### What the matrix asserts

| Case | Expectation |
|------|-------------|
| Identify | Distinct DIDs; federation health OK |
| Private default | New OKH **absent** from `/catalog` |
| Visibility promote | `PUT …/visibility` → appears in `/catalog` |
| Unfollowed reject | Sync without follow does not ingest |
| Follow + sync | B follows A → `/sync/run` → title on B |
| Auto-follow | `sync/run?peer_url=` auto-follows (URL must be reachable **from B**) |
| Unfollow | After unfollow, new records are not ingested |
| Provenance / attestation hop | Ride the catalog to B when present |
| Grants / accounts | **Do not** sync across nodes |
| Rate limit | Burst digest → 429 (may skip if limit high) |
| Background sync | Optional (`RUN_SLOW_CASES=1`) |
| Edge / relay | Optional (`RUN_ROLE_CASES=1`) — edge hides federation API |

**Compose `peer_url` caveat:** `POST /sync/run?peer_url=` is executed inside Peer B.
Use the Compose DNS name (`INTERNAL_PEER_A_URL=http://ohm-peer-a:8001`), not
`http://localhost:8001`. On Azure, set `INTERNAL_PEER_A_URL` to Peer A's public HTTPS origin.

Default API keys (overridden in compose): `fed-test-key-a` / `fed-test-key-b`.

## Topology

```text
┌─────────────────┐         Compose DNS          ┌─────────────────┐
│  ohm-peer-a     │ ◄──── MANUAL_PEERS ────────► │  ohm-peer-b     │
│  localhost:8001 │                              │  localhost:8002 │
│  volume: a      │                              │  volume: b      │
└─────────────────┘                              └─────────────────┘
         ▲                                                ▲
         │         profile: roles (optional)              │
    ┌────┴────┐                                    ┌──────┴──────┐
    │ ohm-edge│ 8003 (federation API 404)          │ ohm-relay   │ 8004
    └─────────┘                                    └─────────────┘
```

Each peer has:

- Separate object storage volume
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
| `OHM_FEDERATION_NODE_ROLE` | `peer` (full), `edge` (no federation API), `relay`/`registry` (API on, no distinct protocol yet) |

## mDNS limitations

mDNS (`_ohm._tcp.local.`) works on real WiFi LANs but is **unreliable inside Docker bridge networks** and **does not work across public-cloud regions**. For Compose, CI, and Azure:

- Set `OHM_FEDERATION_MDNS_ENABLED=false`
- Use `OHM_FEDERATION_MANUAL_PEERS=https://<peer-fqdn>` (or Compose service DNS)

## API endpoints

All routes are under `/v1/api/federation/` when federation is enabled and the
node role exposes the federation API.

| Endpoint | Auth | Description |
|---|---|---|
| `GET /identify` | peer | Node DID, catalog summary |
| `GET /status` | peer | Dashboard status + sync metrics |
| `GET /catalog` | peer | Signed catalog records (shareable visibility only) |
| `GET /records/{content_hash}` | peer | Full signed manifest |
| `POST /sync/digest` | peer | Anti-entropy hash exchange |
| `POST /peers/discover` | **write** | Refresh the local peer registry from manual URLs + mDNS |
| `POST /sync/run` | **write** | Pull missing records from followed peers (`?peer_url=` auto-follows) |
| `POST /peers/{did}/follow` | **write** | Allow ingest from peer |
| `DELETE /peers/{did}/follow` | **write** | Remove allowlist entry |
| `POST /packages/fetch` | **write** | On-demand package fetch from a peer |
| `POST /okw/sync/run` | **write** | Pull OKW records from followed peers |

**"peer"** means anonymous: a peer authenticates with a DID it signs for, not
with one of this node's API keys, so the read side of the protocol and the
digest exchange stay open and are bounded by the per-DID rate limiter instead.

**"write"** means the `write` permission, enforced wherever
`require_auth_for_writes` is on — which peacetime turns on for any
production-like `ENVIRONMENT`. These routes mutate local trust or local storage,
or make this node fetch a URL the caller chose; `POST /sync/run?peer_url=` does
all three at once, auto-following whatever DID the URL claims and ingesting its
manifests. They are ordinary local writes wearing federation clothing, and they
authorize like any other write.

## Production posture

The public instance runs federation **read-only**: enabled, answering
`/identify`, `/status` and `/catalog`, but with `OHM_FEDERATION_MANUAL_PEERS`
and `OHM_FEDERATION_SEED_PEER_URL` unset. That is what makes it read-only —
with no manual peers and nothing followed, the background sync loop iterates an
empty registry and the node makes no outbound peer calls. There is no separate
"read-only" switch.

Settings live in `config/environments/<env>.toml` and reach the container
through `deploy_env_vars()`, which **uppercases each key verbatim**. The keys
must therefore be spelled `ohm_federation_*`: a key named `federation_enabled`
would set `FEDERATION_ENABLED`, which nothing reads — a silent no-op that looks
correct in the diff. `tests/unit/test_config_schema.py` pins this.

`ohm_federation_data_dir` is not optional in a container. The default is
`~/.ohm/federation`, the image's `ohm` user has no home directory, and the
entrypoint's `/app/storage/federation` fallback is a shell variable it never
exports — so identity load raises inside the request handler and every
federation route returns **500 instead of 404**.

### Turning it back off

Deleting the key from the TOML and redeploying is **not** enough.
`deploy_azure.py` applies config with `az containerapp update --set-env-vars`,
which is additive: it adds and updates the listed variables and leaves every
other existing variable alone. Removing a key from the file simply stops
mentioning it, so the value already on the app persists. Turning federation off
is an out-of-band step on both container apps:

```bash
az containerapp update -n <app> -g <rg> --set-env-vars OHM_FEDERATION_ENABLED=false
```

## Trust model

- Peers discovered via mDNS or manual URLs start **unfollowed**
- Sync only **ingests** manifests from **followed** DIDs
- All records must pass signature verification and OKH validation
- **Accounts, API keys, and grants do not federate** — each node has its own auth plane.
  Peer-as-issuer trust (honoring a grant whose issuer DID is a followed peer) is
  local resolution only; there is no grant-import HTTP API yet (unit-tested).

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
# API (matrix script uses this)
curl -X PUT "$PEER_A/v1/api/okh/$ID/visibility" \
  -H "Authorization: Bearer $API_KEY_A" \
  -H "Content-Type: application/json" \
  -d '{"visibility":"public"}'

# CLI
ohm okh visibility set <manifest_id> public
ohm okh visibility show <manifest_id>
```

Visibility is **local** (not carried on the catalog record). A peer that ingests a
design decides independently whether to re-share it. See
[Identity Model — Record visibility](../architecture/identity-model.md).

**Provenance** and **attestations** *do* ride the node-signed catalog record (out of
the design content hash). On ingest, signed provenance/attestations are verified
and re-stamped into the peer's own stores. See
[Identity Model](../architecture/identity-model.md).

### Bidirectional sync and conflicts

Sync is **pull-based**: mutual follow + each side runs sync (or background sync).

Ingest policy (**first-write-wins**):

| Situation | Result |
|---|---|
| Same content hash already local | `skipped` / `already_present` |
| Same manifest id, identical content (incl. private ingest) | `skipped` / `already_present` |
| Same manifest id, divergent content | `skipped` / `id_conflict` (local kept) |
| New id + new hash | `stored` |

`OHM_FEDERATION_SYNC_RATE_LIMIT_PER_MIN` caps **digest** exchange, not
`GET /records/{hash}`. Global HTTP middleware also skips `/v1/api/federation/*`.

### Package artifacts (separate channel)

When a shareable OKH has a local package, the catalog record includes a
`package` pointer (`bundle_hash`, `byte_size`, `filename`). Peers do **not**
pull zip bytes during catalog sync.

```bash
# On-demand fetch (serving peer must follow the requester DID)
ohm federation package-fetch \
  --peer http://ohm-peer-a:8001 \
  --bundle-hash sha256:… \
  --manifest-id <okh-uuid>
```

`POST /v1/api/federation/packages/fetch` tries peer blob download first, then
rebuilds from OKH URLs if fetch fails. Blob GET requires header
`X-OHM-Peer-DID` of a followed peer.

### OKW catalog (separate Merkle root)

OKW facilities use a **separate** federation catalog from OKH. Shareable
facilities export a **redacted projection** based on disclosure profiles
(`followers` / `public` field groups). Default is fail-closed (**identity only**).

```bash
ohm okw disclosure show <facility_id>
ohm okw disclosure set <facility_id> followers identity location
ohm okw disclosure preview <facility_id> followers   # redacted JSON + exported flag
ohm okw visibility set <facility_id> followers
ohm federation okw-sync
```

`GET /v1/api/okw/{id}/disclosure/preview?audience=followers|public` returns the
same redacted facility dict the OKW catalog would sign for that audience, plus
`exported` (false while visibility is `private` or does not match the audience).
The facility detail UI uses this preview so operators see what peers will get.

Federation endpoints: `GET /v1/api/federation/okw/catalog`, `…/okw/records/{hash}`,
`POST …/okw/sync/digest`, `POST …/okw/sync/run`.

## CLI

```bash
ohm federation status
ohm federation peers --discover
ohm federation follow did:key:...
ohm federation sync --peer http://ohm-peer-a:8001
ohm federation okw-sync
ohm federation package-fetch --peer http://ohm-peer-a:8001 --bundle-hash sha256:…
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

Relay and registry nodes are planned for Cloud Run + Firestore to support NAT'd **edge** nodes. The LAN HTTP sync protocol remains the same; only discovery and connectivity layers change. Today `relay`/`registry` roles expose the federation API but have **no distinct protocol** — the matrix documents that.
