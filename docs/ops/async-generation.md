# Async generate-from-url (Celery worker)

Generating an OKH manifest from a repository takes longer than an HTTP request
should. `POST /api/okh/generate-from-url/jobs` therefore enqueues one Celery job
per URL and returns immediately; the client polls for progress. This page covers
running that in a deployed environment.

For the local Compose setup (`ohm-worker` + Redis), see `docker-compose.yml` —
nothing here is needed to develop against it.

## What has to be true

Three things, and the feature is off unless **all** of them hold:

| Requirement | Where it comes from |
|---|---|
| `JOBS_ENABLED=true` | `jobs_enabled` in `config/environments/<env>.toml` |
| `JOB_BROKER_URL` (+ `JOB_RESULT_BACKEND`) | minted as container-app secrets by the deploy |
| A running Celery worker | its own container app, deployed separately |

`jobs_available()` is the AND of the first two, so the API returns **503** with
an explanatory message when either is missing. That 503 is deliberate and
honest: the endpoints refuse rather than accept work nothing will do.

!!! warning "Enabling the flag without a running worker is worse than the 503"
    The capacity check treats an unreachable broker as "zero jobs in flight", so
    submissions are **accepted** and then sit in `PENDING` forever — no error, no
    timeout, a progress bar stuck at 0%. Deploy the worker first, or together.

## Redis layout

One Azure Cache for Redis instance serves both the catalogue cache and Celery,
split by database — the same split `docker-compose.yml` uses:

| Database | Use |
|---|---|
| 0 | catalogue cache |
| 1 | Celery broker |
| 2 | Celery results |

Staging uses 3/4/5 on the same instance, so it shares no queue with production.

The connection URLs are **not** checked in. Each deploy reads the access key
from Azure and mints all three URLs as container-app secrets, which means
rotating the key needs no repo change and two apps pointed at one instance
cannot drift apart. The non-secret half — host, port, database indices — lives
in the `[redis]` table of the environment's config file.

Both URLs carry `?ssl_cert_reqs=required`. Without it, a `rediss://` URL is
parsed with certificate verification **disabled**, silently.

## Deploying the worker

The worker runs the same image as the API in `worker` mode, with no ingress.

```bash
uv run python deploy/scripts/deploy_azure_worker.py \
    --image <the same image the API is running> \
    --subscription-id <subscription> \
    --environment production
```

It creates the container app if it does not exist. Its environment comes from
the shared config surface — the top-level settings plus `[worker.env]` — so the
storage target is declared once and the API and worker cannot point at different
data. Shape (cpu, memory, replicas) comes from `[worker]`.

Two constraints worth knowing before you rename anything:

- **Replicas are pinned at 1.** The platform's default autoscaler is HTTP-based,
  and a worker with no ingress never receives HTTP. Scaling to zero without an
  explicit queue-length rule means jobs are accepted and never run.
- **Container app names cap at 32 characters.** `openhardwaremanager-worker`
  (26) fits; an environment-suffixed variant may not.

The worker mirrors the storage key and both git access tokens from the API app
on every deploy, so the copies cannot diverge. It needs the git tokens because
**the worker**, not the API, clones the repositories — without them every
generation hits anonymous rate limits and users see a rate-limit error.

## Is it healthy?

The platform's probes are HTTP/TCP only, so the Compose healthcheck
(`celery inspect ping`) does not transfer — and a worker whose pool is wedged
answers ping anyway while consuming nothing. The real check is end to end:

```bash
uv run python -m harness.runner --modules probe_async_generation
```

It submits a real job against a small public repository, polls to a terminal
state, and fails if the job does not complete in time. It distinguishes
*accepted but never consumed* (no worker on the queue) from *ran but did not
finish*, because the fixes are different.

For a quick manual look at the worker itself:

```bash
az containerapp logs show -n openhardwaremanager-worker -g project_data_rg --tail 50
```

A healthy worker logs a `celery@… ready.` banner, the broker it connected to,
and `concurrency: 1 (prefork)`. Confirm the transport line shows the database
index you expect — a worker on the wrong database is invisible to the API.

## Do the two apps agree?

Both deploys mirror the shared secrets from the API app on every run, so they
cannot drift across a deploy. To confirm that took effect — and to catch a
half-completed deploy or a secret edited by hand in the portal since:

```bash
make secrets-check
```

It compares **digests**, never values, so the output is safe to paste into an
issue. `api-key` is expected on the API only; a worker authenticates no callers.

The important line is `job-broker-url`. If the API and worker point at different
Redis databases, jobs are accepted and never consumed, and **nothing in either
app looks wrong** — you only see it by comparing the two.

## Reading a failed job

`GET /api/okh/generate-from-url/jobs/{job_id}` reports `state`, `stage`,
`fraction`, and on failure an `error`.

| Symptom | Likely cause |
|---|---|
| 503 on submit | `JOBS_ENABLED` or `JOB_BROKER_URL` missing on the API |
| Stuck at `PENDING`, 0% | No worker consuming — check the worker app is running and its broker URL matches the API's |
| 429 on submit | Per-IP rate limit, or the concurrency/queue caps are full |
| `FAILURE` with a rate-limit error | Git tokens missing **on the worker** |
| `FAILURE` on a large repository | Worker memory; generation loads spaCy and clones the repo |
| Progress resets to 0% mid-run | The worker was redeployed. Tasks are acknowledged late, so the job was requeued rather than lost — it restarts from the beginning |

Generated manifests are held in the result backend for 24 hours and then expire.

## Generation quality

Generation prefers an LLM layer but degrades to direct + heuristic + NLP when no
provider key is configured, which is the current deployed state. The degradation
is silent by design — the job succeeds either way — but heuristic-only output
typically leaves `function` empty, and that is a required OKH field. The guided
review in the UI asks for it before enabling download, so expect to write one
sentence per generated manifest.

## Secrets in Key Vault

Container App secrets are per-app, so every value the API and worker share once
existed twice. They are now **references**: the value lives once in Key Vault and
both apps hold a pointer, resolved at runtime through their system-assigned
managed identity. Rotation is one edit rather than an edit plus a redeploy of
everything downstream.

Migrating an environment:

```bash
uv run python deploy/scripts/migrate_secrets_to_key_vault.py \
    --environment production --vault-name <vault> \
    --container-app-name openhardwaremanager \
    --worker-app-name openhardwaremanager-worker \
    --deploy-principal-id <CI principal object id> --dry-run
```

Run the dry run first, and **rehearse on staging before production**: an app that
cannot resolve a secret does not start, which in production is an outage.

The order is not arbitrary — identities and access must exist before any app is
repointed, or the repointed app cannot start:

1. Create the vault (RBAC-authorised).
2. Enable a system-assigned identity on each app.
3. Grant each identity **Key Vault Secrets User**; grant the operator and the CI
   deploy principal **Key Vault Secrets Officer** (both write).
4. Copy current values in from the API app.
5. Repoint both apps.
6. Verify: health, worker logs, and the end-to-end job probe.

!!! warning "An RBAC vault grants Owners nothing on the data plane"
    Subscription Owner is a management-plane role. Without an explicit
    **Secrets Officer** grant, writing secrets fails with a bare 403 partway
    through, leaving the vault half-populated. The migration script grants the
    operator this before it writes.

### Two constraints worth knowing

- A Container App secret name carrying a Key Vault reference **cannot exceed 20
  characters**. `llm-encryption-password` was 23, so the secret is now
  `llm-encrypt-password`. Only the secret's name changed; the environment
  variable the application reads is unchanged.
- Rotation needs no deploy, but is **not instant** — the platform caches
  Key Vault-backed secret values and refreshes on its own schedule. Plan
  rotations accordingly rather than expecting immediate effect.

### Tearing an environment down

`teardown_azure_environment.py` removes the container apps, and — when asked —
the blob container and the Key Vault. Both destructive options are opt-in, and
production is refused twice over: by environment name, and by the live app and
vault names.

```bash
uv run python deploy/scripts/teardown_azure_environment.py \
    --environment staging --yes --delete-blob-container --delete-key-vault
```

`--delete-key-vault` also **purges**. That is deliberate: a soft-deleted vault
keeps its name reserved for 90 days, so a delete without a purge silently blocks
the next rebuild of that environment with a name collision. Purging is
irreversible, which is why it is opt-in.

### Deploys write references, never values

Where an environment declares `key_vault_name`, the deploy scripts set secret
**references** on the apps and mint the Redis URLs **into the vault**. They never
set a secret value on a container app.

That is not a stylistic preference. Setting a secret by name *replaces* a Key
Vault reference with an inline value, so a deploy that wrote values would
succeed, leave both apps working, and silently undo the migration — putting the
duplicated copies back with nothing to signal it. `make secrets-check` reports
any value found inline for exactly this reason.

Environments with no `key_vault_name` are unaffected and still stand up the old
way, which is what makes a fresh self-host environment possible.

### Renaming a secret

Do it additively, in this order, because an app that resolves the wrong name
does not fail loudly — a missing GitHub token just means anonymous cloning, and
anonymous rate limits look like intermittent 429s during generation.

1. Create the new secret in the vault with the same value; confirm the digests
   match before going further.
2. Change the name in the deploy constants.
3. Deploy. Both apps gain a reference to the new name and their env vars follow.
4. Verify, then delete the old vault secret and the leftover app secrets.

The old secret stays resolvable throughout, so there is no window where an app
is pointed at something that does not exist.

### Leftovers

The migration replaces secrets by name and touches nothing else, so a
pre-rename secret such as `llm-encryption-password` remains, unreferenced.
Removing leftovers is a **separate** step once the references have been trusted
in production — not part of the cutover, where an unnecessary deletion is one
more way to lose a value you still need.
