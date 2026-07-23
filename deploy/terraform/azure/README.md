# Azure Terraform for OHM (self-host + ephemeral federation lab)

Public IaC for running **Open Hardware Manager** on Azure Container Apps.
This is the greenfield path for self-hosters and for ephemeral multi-region
federation validation. Production CD continues to use
[`deploy/scripts/deploy_azure.py`](../../scripts/deploy_azure.py) against the
existing `project_data_rg` apps — **this stack never touches production**.

## What you get

| Resource | Purpose |
|----------|---------|
| Disposable resource group | `ohmfed-<suffix>-rg` |
| Per-node storage account + container | Isolated catalogs |
| Per-node Container Apps Environment | Regional ACA |
| Container App (API) | OHM image with federation enabled |
| Random `API_KEYS` | Per-node admin/write auth |

Default topology (ephemeral federation lab):

| Node | Role | Region |
|------|------|--------|
| Peer A | `peer` | westus3 |
| Peer B | `peer` | eastus |
| Edge | `edge` (federation API **404**) | westus3 |
| Relay | `relay` (API on; **no distinct protocol yet**) | westus2 (avoids competing with peer_b for ACA env capacity in eastus) |

Consumption Container Apps require fixed **CPU + memory pairs** (e.g. `0.5` + `1Gi`,
`1.0` + `2Gi`). Invalid pairs like `1` CPU with `4Gi` are rejected by Azure.

Log Analytics and ACA Environment names include the region slug. Changing
`relay_location` (or any node location) **replaces** those resources rather than
trying to move them — Azure does not allow the same name in a new region inside
one resource group (`InvalidResourceLocation`).

Ephemeral nodes use `ENVIRONMENT=test` so they boot without
`LLM_ENCRYPTION_*` secrets. For a production-like self-host, set
`ENVIRONMENT=production` and supply those encryption secrets (and prefer
`0.5` CPU / `1Gi` or a valid Consumption pair).

## Prerequisites

- Azure CLI (`az login`) with permission to create RGs / ACA / storage
- [Terraform](https://developer.hashicorp.com/terraform/install) ≥ 1.5
- Public Docker Hub image (default `touchthesun/openhardwaremanager:0.10.0`)

## Ephemeral federation lab (recommended test path)

```bash
# From repo root
cp deploy/terraform/azure/environments/federation-ephemeral.tfvars.example \
   deploy/terraform/azure/environments/federation-ephemeral.tfvars

./deploy/terraform/azure/scripts/up.sh
# two-pass apply: create nodes, then wire OHM_FEDERATION_MANUAL_PEERS to HTTPS FQDNs

eval "$(terraform -chdir=deploy/terraform/azure output -raw matrix_env)"

# Optional: asymmetric catalogs before sync
./scripts/federation_seed_azure.sh

# Same suite as Compose (URL-parameterized)
./scripts/federation_matrix.sh
RUN_ROLE_CASES=1 ./scripts/federation_matrix.sh

# Tear down everything (RG + storage + apps)
./deploy/terraform/azure/scripts/down.sh
```

**Cost / idle policy:** leave `min_replicas = 1` only while actively testing.
Set `min_replicas = 0` in the tfvars if you pause briefly, then always
`down.sh` when finished. Destroy removes the resource group; leftover charges
should be ~$0 after destroy completes. Node DIDs live on ephemeral app
filesystem — **destroy loses federation identity**.

## Single-node self-host (minimal)

1. Copy `modules/ohm_node` usage from `main.tf` into a thin root that creates
   one RG + one `ohm_node` module with `node_role = "peer"`.
2. Set `manual_peers` to `""` or a comma-separated list of peer HTTPS origins.
3. `terraform apply`, then point a reverse proxy or the frontend image's
   `API_UPSTREAM_URL` at the output `fqdn`.

Federation env vars applied by the module:

- `OHM_FEDERATION_ENABLED=true`
- `OHM_FEDERATION_MDNS_ENABLED=false` (mDNS does not work across regions)
- `OHM_FEDERATION_MANUAL_PEERS=<https peers>`
- `OHM_FEDERATION_NODE_ROLE=peer|edge|relay|registry`
- `STORAGE_PROVIDER=azure_blob` + dedicated account/container

## Validation notes

Local Compose matrix first: see
[docs/development/federation-infra.md](../../../docs/development/federation-infra.md).

Expected MVP behaviour on live peers:

- OKH catalog sync works with visibility + follow
- Accounts / grants / API keys **do not** propagate
- Edge role hides `/v1/api/federation/*`
- Relay role looks like a peer for catalog sync until v0.2 protocol exists

Capture Azure run results in [`docs/testing/federation-azure-validation.md`](../../../docs/testing/federation-azure-validation.md).
