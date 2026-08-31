---
title: Deploy a node on Azure
area: selfhost
surface: selfhost
---

# Deploy a node on Azure

This stands up a **new** OHM environment on Azure Container Apps — your own
resource group, storage, API, and (when you want them) background-generation
workers. It does **not** change the public openhardwaremanager.org deployment;
that stack is separate.

!!! note "One option, not the default"

    Self-hosting does not require Azure or any cloud account.
    [Run your own node](run-your-own-node.md) is the supported path everywhere,
    including on a server you own — it's one `docker compose up`, and it's what
    to use unless you specifically want managed infrastructure.

    This guide exists because it's what the public instance runs, so it's the
    cloud path we can keep honest. There is no equivalent for AWS or Google
    Cloud; both are supported as *storage* backends, with compute via Compose on
    a VM.

You need the OHM source tree (the Terraform lives under
`deploy/terraform/azure/`), an Azure subscription you can create resources in,
and a published OHM container image.

## What gets created

| Piece | Role |
|-------|------|
| Resource group | Isolates the environment so you can tear it down cleanly |
| Storage account + container | Where designs, facilities, and packages live |
| Container Apps environment | Runs the API (and optional worker) |
| API Container App | The OHM service, with a random admin `API_KEYS` value |
| Redis + worker *(optional)* | Celery broker and background worker for async generate-from-url |
| Encryption secrets *(production)* | `OHM_ENCRYPTION_SALT` / `OHM_ENCRYPTION_PASSWORD` so admins can store LLM keys in Settings |

## Prerequisites

- Azure CLI, logged in (`az login`) with permission to create resource groups,
  Container Apps, storage, and (if you enable jobs) Azure Cache for Redis
- [Terraform](https://developer.hashicorp.com/terraform/install) 1.5 or newer
- A pullable image, for example `touchthesun/openhardwaremanager:<version>` —
  pin an explicit version; don't track `latest` for anything you depend on

## Fastest path: one peer with jobs

The repository includes a minimal single-node example at
`deploy/terraform/azure/examples/single-peer/`. Copy that root (or the
`ohm_node` module usage from `deploy/terraform/azure/main.tf`) into a working
directory, then set at least:

```hcl
environment = "production"   # provisions LLM encryption secrets
enable_jobs = true           # Redis + Celery worker + JOBS_ENABLED on the API
image       = "touchthesun/openhardwaremanager:<version>"
```

Apply from that directory:

```bash
terraform init
terraform apply
```

The module outputs the API hostname (`fqdn`) and a sensitive admin API key.
Point a reverse proxy — or the frontend image's `API_UPSTREAM_URL` — at that
HTTPS origin.

### What `enable_jobs` and `environment` do

| Setting | Effect |
|---------|--------|
| `enable_jobs = true` | Provisions Redis and a no-ingress worker app; sets `JOBS_ENABLED`, `JOB_BROKER_URL`, and `JOB_RESULT_BACKEND` on the API |
| `enable_jobs = false` | API only (default on the multi-peer federation lab, to control cost). Generate-from-url still works **synchronously**, but long runs can hit proxy timeouts |
| `environment = "production"` | Boots with real LLM encryption secrets so **Settings → LLM providers** can store keys |
| `environment = "test"` | Fine for short-lived labs; the app will refuse to persist LLM keys against development defaults |

Async import behaviour is described in
[Import from a URL](import-from-a-url.md).

## Multi-peer federation lab

If you need several regional peers to exercise federation (not a permanent
self-host), use the ephemeral lab under `deploy/terraform/azure/`:

```bash
cp deploy/terraform/azure/environments/federation-ephemeral.tfvars.example \
   deploy/terraform/azure/environments/federation-ephemeral.tfvars

# Optional: enable_jobs = true / environment = "production" in the tfvars
# when you want the same job stack on every peer (costs more).

./deploy/terraform/azure/scripts/up.sh
```

`up.sh` runs a two-pass apply so peer URLs can be wired into
`OHM_FEDERATION_MANUAL_PEERS`. Tear everything down with
`./deploy/terraform/azure/scripts/down.sh` when finished — destroy removes the
resource group; leftover cost should be ~zero after that completes.

Federation identity for those nodes lives on ephemeral app filesystem:
**destroy loses it.**

## After the first apply

1. Open `https://<fqdn>/health` and confirm the instance reports healthy storage.
2. Authenticate with the outputted `API_KEYS` value
   (`Authorization: Bearer …`).
3. If you set `environment = "production"`, add an LLM provider under
   **Settings → LLM providers** (or keep using process env keys).
4. If you set `enable_jobs = true`, run a generate-from-url import and confirm
   the UI shows a progress bar rather than hanging on a long request — see
   [Import from a URL](import-from-a-url.md).

Day-to-day self-host expectations (storage, upgrades, access control) are in
[Run your own node](run-your-own-node.md).

## What this path is not

- It is **not** the CD pipeline for the public OHM instance. That continues to
  use a separate deploy script against an existing resource group.
- Turning jobs on for that public stack requires the same Redis + worker
  wiring there; publishing a new API image alone does not enable background
  generation.

Operator detail (variable reference, CPU/memory pairs, idle cost policy) stays
in `deploy/terraform/azure/README.md` in the source tree.
