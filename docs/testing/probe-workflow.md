# Production probe workflow

Last updated: 2026-07-08

Targeted **probes** diagnose the four Azure Container Apps pain points observed
after the first cloud UI deployment. They follow the same harness protocol as
verification loops (`discover → observe → judge → report`) but issue live HTTP
requests against a running API.

**Workflow:** probe → draft proposal → human review → implementation issue → build.

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
- [`harness/README.md`](../../harness/README.md)

## ACA deployment: match cold start

Set these on the API container (Azure Container Apps env / secretRef):

| Variable | Default | Purpose |
|----------|---------|---------|
| `MATCHING_EAGER_INIT` | `true` | Pre-load MatchingService during app startup |
| `MATCHING_INIT_TIMEOUT_SECONDS` | `120` | Max wait for spaCy/NLP init at startup and in Depends |
| `MATCHING_PREINIT_NLP` | `true` | Load spaCy at init (set `false` only if NLP deferred) |

Point ACA **readiness** at `/health/readiness` (not `/health`) so traffic waits until matching is warm. Verify with `make harness-probes` → `probe_match` clean.
