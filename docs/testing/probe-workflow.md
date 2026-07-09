# Production probe workflow

Last updated: 2026-07-08

Targeted **probes** diagnose the four Azure Container Apps pain points observed
after the first cloud UI deployment. They follow the same harness protocol as
verification loops (`discover → observe → judge → report`) but issue live HTTP
requests against a running API.

**Workflow:** probe → draft proposal → human review → implementation issue → build.

---

## Progress (ACA production, v0.8.9)

First cloud UI deployment triage — status as of **2026-07-08** after `v0.8.9` is
live on Azure Container Apps (`openhardwaremanager…westus3.azurecontainerapps.io`).

| Probe | Pain point | Issue | Status | Outcome |
|-------|------------|-------|--------|---------|
| `probe_match` | Intermittent POST `/match` **503** | [#270](https://github.com/helpfulengineering/supply-graph-ai/issues/270) | **Resolved** | `MATCHING_EAGER_INIT` + `/health/readiness` `matching_service` check; frontend shows `request_id` on errors. Probe clean post-deploy. |
| `probe_cache` | **Missing cache** on hot reads | [#271](https://github.com/helpfulengineering/supply-graph-ai/issues/271) | **Resolved** | Unified `CacheBackend` (`memory` / `redis`); ACA on Azure Managed Redis (`CACHE_BACKEND=redis`). Metrics at `/v1/api/utility/metrics` → `data.cache`. Site noticeably more responsive. |
| `probe_latency` | **10–30s** responses | — | **Improved** | Latency down with warm matching + Redis; `okh_list` may still warn on SLO — monitor, no dedicated issue yet. |
| `probe_okh_files` | **OKH file links** broken | [#272](https://github.com/helpfulengineering/supply-graph-ai/issues/272) | **In progress** | File proxy API + frontend landed; verify on ACA with `make harness-probes`. |

### Release / ops lessons (0.8.9)

| Topic | What happened | Fix |
|-------|---------------|-----|
| Deploy verify hang | `curl \| json.load` on empty responses during cold start; 100s window too short | Release workflow: robust retry loop, `/health/liveness`, flushed logs |
| Container crash loop | Gunicorn `nproc*2+1` → 3 workers on 1 vCPU, each eager-loading spaCy | `GUNICORN_WORKERS=1`, `GUNICORN_TIMEOUT=300` in `production.toml` + entrypoint defaults |
| Frontend deploy | `ServiceConfig` rejected `0.5` CPU | Allow fractional CPU (min `0.25`) for nginx SPA container |
| GitHub Release job | Missing `## [0.8.9]` in `CHANGELOG.md` | Changelog section added; gate requires section per tag |

### Verification commands

```bash
# Quick live check
curl -sS https://openhardwaremanager.blackdune-e38fce01.westus3.azurecontainerapps.io/health | jq .

# Full probe sweep (point harness.config.json at ACA first)
make harness-probes
```

**Next:** deploy #272 to ACA, run `make harness-probes` until `probe_okh_files` is clean, then close the triage loop.

---

## Pain points and probes

| Probe | Pain point | What it checks |
|-------|------------|----------------|
| `probe_match` | Intermittent POST `/match` **503** | N repeated match calls; 503 rate, `X-Request-Id`, API `detail` |
| `probe_latency` | **10–30s** responses | Configurable GET/POST checks vs warn/error SLO (ms) |
| `probe_cache` | **Missing cache** on hot reads | Static `@cache_response` scan + double-GET speedup / `_cached` flag |
| `probe_okh_files` | **OKH file links** broken | Manifest file refs: relative paths vs unreachable externals |

Probes are **disabled by default** in `harness.config.json` so local `make harness`
(verification loops only) stays fast. Enable them when pointing at staging/production.

---

## Running probes

### 1. Point config at staging

Edit `harness.config.json`:

```json
{
  "api_base_url": "https://your-aca-api.example.com",
  "api_health_url": "https://your-aca-api.example.com/health",
  "api_path_prefix": "/v1/api",
  "modules": {
    "probe_match": { "enabled": true, "options": { "skip_if_unreachable": false } },
    "probe_latency": { "enabled": true },
    "probe_cache": { "enabled": true },
    "probe_okh_files": { "enabled": true, "options": { "okh_id": "optional-fixed-id" } }
  }
}
```

Set `OHM_API_KEY` if the deployment requires auth (same as other API clients).

### 2. Run probes and emit proposals

```bash
make harness-probes
# or
uv run python -m harness.runner --probes --write-proposals
```

On ERROR findings, draft markdown files land in `docs/proposals/` (one per finding).
Use [`docs/proposals/TEMPLATE.md`](../proposals/TEMPLATE.md) for manual proposals.

### 3. Human review

- Confirm root cause from probe evidence (not just symptoms).
- Refine the auto-generated proposal: scope, acceptance criteria, rollout.
- Approve → create implementation issue → build fix.
- Re-run probes on staging until clean.

---

## CLI flags

| Flag | Effect |
|------|--------|
| `--loops` | Verification loops only (default for `make harness`) |
| `--probes` | Production probes only |
| `--modules a,b` | Explicit subset |
| `--write-proposals` | Write `docs/proposals/probe_*-*.md` for ERROR findings |
| `--json` | Machine-readable report |

---

## Skip behavior

Probes skip when `skip_if_unreachable: true` (default) and `/health` is down.
For staging triage, set `skip_if_unreachable: false` so unreachable API fails
closed.

---

## Related docs

- [Triage harness operator reference](triage-harness.md)
- [Distributed cache deployment](cache-deployment.md) — `CACHE_BACKEND` memory vs Redis (#271)
- [`harness/README.md`](../../harness/README.md)

## ACA deployment: match cold start

Set these on the API container (Azure Container Apps env / secretRef):

| Variable | Default | Purpose |
|----------|---------|---------|
| `MATCHING_EAGER_INIT` | `true` | Pre-load MatchingService during app startup |
| `MATCHING_INIT_TIMEOUT_SECONDS` | `120` | Max wait for spaCy/NLP init at startup and in Depends |
| `MATCHING_PREINIT_NLP` | `true` | Load spaCy at init (set `false` only if NLP deferred) |

Point ACA **readiness** at `/health/readiness` (not `/health`) so traffic waits until matching is warm. Verify with `make harness-probes` → `probe_match` clean.

**Gunicorn on ACA (1 vCPU):** use `GUNICORN_WORKERS=1` and `GUNICORN_TIMEOUT=300`. The default `nproc*2+1` workers each run eager NLP init and can OOM or exceed the 120s worker timeout on a 2Gi container. These are set in `config/environments/production.toml` and applied by the release deploy step.
