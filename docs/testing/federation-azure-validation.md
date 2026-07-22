# Federation Azure validation — 2026-07-21

## Compose matrix (executed 2026-07-21)

```bash
docker compose -f docker-compose.federation.yml --profile roles up -d
RUN_ROLE_CASES=1 EDGE_URL=http://localhost:8003 RELAY_URL=http://localhost:8004 \
  ./scripts/federation_matrix.sh
```

**Result:** `passed=15 failed=0 skipped=3` (green)

| Case | Result |
|------|--------|
| Identify + health | PASS |
| Private default | PASS |
| Unfollowed reject | PASS |
| Visibility promote | PASS |
| Follow + sync (OKH store on B) | PASS |
| Bidirectional B→A + round-trip | PASS |
| Sync idempotency (re-sync pulled=0) | PASS |
| OKW disclosure + catalog sync | *(matrix cases added)* |
| Package CAS pointer + on-demand fetch | *(matrix cases added; may SKIP without package assets)* |
| Auto-follow via `peer_url` | PASS |
| Unfollow | PASS |
| Provenance hop | PASS |
| Attestation hop | SKIP (issued on A; not yet on B catalog — follow-up) |
| Grants do not propagate | PASS |
| Accounts do not propagate | PASS |
| Peer-as-issuer positive | SKIP (no grant-import/resolve HTTP API; unit-covered) |
| Rate limit 429 | PASS |
| Background sync | SKIP (needs `RUN_SLOW_CASES=1`) |
| Edge federation 404 | PASS |
| Relay API + role=relay | PASS |

### Findings

1. **Ingested OKH on followers is private by default** — appears in `GET /v1/api/okh` but not in `GET /v1/api/federation/catalog` until the follower re-shares. Matrix asserts on the OKH store for sync success.
2. **`POST /okh/create` 500 after save** — fixed in **0.10.1** (`OKHResponse`
   missing `message`/`status`). Ephemeral peers on Hub `0.10.0` still show matrix
   workaround noise until rebuilt on `0.10.1`.
3. **Compose must force `STORAGE_PROVIDER=local`** — inheriting host `.env` Azure production storage hangs `/identify` (full catalog list).
4. **`sync/run?peer_url=` must use a URL reachable from Peer B** (`INTERNAL_PEER_A_URL=http://ohm-peer-a:8001` in Compose; public HTTPS on Azure).
5. **Accounts/grants do not federate** — confirmed. Peer-as-issuer remains local resolution only.
6. **Edge/relay** — capability flags only; edge hides federation API; relay looks like a peer for catalog until v0.2.

## Azure ephemeral stack (IaC ready; apply pending)

Terraform lives at [`deploy/terraform/azure/`](../../deploy/terraform/azure/). This agent
environment did not have a working `terraform` / `az` session to apply live.

### Operator runbook

```bash
# Install terraform >= 1.5; az login
cp deploy/terraform/azure/environments/federation-ephemeral.tfvars.example \
   deploy/terraform/azure/environments/federation-ephemeral.tfvars

./deploy/terraform/azure/scripts/up.sh
eval "$(terraform -chdir=deploy/terraform/azure output -raw matrix_env)"
./scripts/federation_seed_azure.sh
./scripts/federation_matrix.sh
RUN_ROLE_CASES=1 ./scripts/federation_matrix.sh

# Cost: destroy when idle
./deploy/terraform/azure/scripts/down.sh
```

### Teardown / cost policy

- `down.sh` runs `terraform destroy` on the disposable RG (apps, ACA envs, storage, keys).
- Set `min_replicas = 0` in tfvars only for a short pause; always destroy when finished.
- Destroy loses node DIDs (ephemeral app filesystem).
- Production (`project_data_rg` / `openhardwaremanager`) is never referenced.

## Follow-ups

- Rebuild/publish image with OKH create response fix so Azure Hub tag does not need the 500 workaround.
- Harden attestation hop (ensure catalog rebuild includes new attestations before B sync).
- Optional grant-import admin API for peer-as-issuer multi-node E2E.
- Real relay protocol (v0.2).
