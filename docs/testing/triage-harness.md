# Triage harness — operator reference

Last updated: 2026-07-08

Multi-loop post-deploy verification for OHM after the first cloud UI deployment.
Four independent loops detect **inventory drift**, **API/client contract drift**,
**RED signals** (rate / errors / duration), and **synthetic UI smoke** against a
live backend.

This document is the **operator reference**. Implementation notes live in
[`harness/README.md`](../../harness/README.md).

---

## What was built (session summary)

| Deliverable | Purpose |
|-------------|---------|
| `harness/` package | Loadable loop modules + CLI runner |
| `harness.config.json` | URLs, thresholds, per-module enablement |
| `make harness` | Run all enabled loops |
| `tests/parity/inventory.py` | Shared FE/BE enumeration (also used by `make parity`) |
| `tests/parity/manifest.py` | Extended with `fe_routes` + `fe_api_prefixes` |
| Unit tests | `tests/unit/test_harness.py`, `test_*_loop.py` (×4 modules) |

### Four loops (all online)

| Module | Detects | Default data source |
|--------|---------|---------------------|
| `client_drift` | Live OpenAPI ops missing from committed `schema.d.ts` | In-process `api_v1.openapi()` |
| `parity` | Service / API tag / CLI / FE route / FE API prefix drift | Code enumeration vs manifest |
| `red` | Per-endpoint error rate & latency threshold breaches | In-process `MetricsTracker` |
| `synthetic_smoke` | Real-api Playwright journey failures | `frontend/e2e` specs |

### Relationship to existing gates

```
make ready          → merge gate (format, lint, unit tests, parity pytest, docs, …)
make frontend-ready → UI build gate (mocked Playwright, no backend)
make harness        → post-deploy triage (this document)
make parity         → subset of parity loop; pytest ratchet on manifest
```

The triage harness **does not** replace `make ready` or `make frontend-ready`.
It is designed for stealth-mode cloud triage: fail-closed on ERROR findings,
graceful SKIP when prerequisites are missing.

---

## Prerequisites

### Always (static loops)

These run without a live API or browser:

- `client_drift` — compares in-process OpenAPI to committed types
- `parity` — enumerates service / API / CLI / FE inventory from source

### Optional (live loops)

| Loop | Requires |
|------|----------|
| `red` (in-process) | Nothing extra; empty metrics → clean |
| `red` (http mode) | API reachable at `api_base_url` |
| `synthetic_smoke` | API up **and** Playwright Chromium installed |

### One-time frontend setup

```bash
make frontend-setup
```

Installs npm deps, Playwright **Chromium + headless shell**, and verifies a
headless launch succeeds. Required before `synthetic_smoke` will run (not skip).

### Smoke prerequisites (typical local run)

```bash
docker compose up -d          # OHM API on :8001
make frontend-setup           # Playwright browsers
uv run python -m harness.runner --modules synthetic_smoke
```

Playwright boots the Vite dev server automatically (`frontend/harness.config.json`
→ `appStartCommand` / `appUrl`).

---

## Running the harness

### All loops

```bash
make harness
# equivalent:
uv run python -m harness.runner
```

### Subset of loops

```bash
uv run python -m harness.runner --modules client_drift,parity
uv run python -m harness.runner --modules synthetic_smoke
```

### Machine-readable output (CI / automation)

```bash
uv run python -m harness.runner --json
uv run python -m harness.runner --modules red --json | jq '.modules[0].findings'
```

### List modules

```bash
uv run python -m harness.runner --list
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | All ran modules are `ok` (no ERROR-severity findings; SKIPPED is ok) |
| `1` | At least one module has ERROR findings, or a module `FAILED` |

**Note:** WARN findings (e.g. RED threshold breaches, stale schema ops) do
**not** fail the harness — they surface signal for triage without blocking.

---

## Interpreting output

Human output example:

```
✓ [online] client_drift: clean
✗ [online] parity: 2 finding(s)
    - (error/gap) Frontend route: undeclared in manifest (1)
      ops: /mystery
✓ [skipped] synthetic_smoke: skipped (API unreachable at http://localhost:8001/health)
✓ [online] red: clean

harness: FAILED (0 stub, 2 online)
```

| Status | Meaning |
|--------|---------|
| `online` | Module ran and judged observations |
| `skipped` | Prerequisites missing; not a failure |
| `failed` | Module threw an exception |
| `stub` | Reserved for future modules not yet implemented |

### Finding shape (JSON)

Each finding includes:

- `kind` — `bug` | `perf` | `gap`
- `severity` — `info` | `warn` | `error`
- `title`, `evidence`, `suggested_state` (default `needs-triage`)

---

## Configuration (`harness.config.json`)

Repo-root JSON file. Key top-level fields:

| Key | Default | Used by |
|-----|---------|---------|
| `api_base_url` | `http://localhost:8001` | RED http mode, docs |
| `api_health_url` | `http://localhost:8001/health` | synthetic_smoke skip probe |
| `openapi_url` | `http://localhost:8001/v1/openapi.json` | client_drift (docs / future http) |
| `frontend_url` | `http://localhost:5173` | synthetic_smoke (via Playwright config) |
| `frontend_dir` | `frontend` | parity, synthetic_smoke |
| `committed_schema` | `frontend/src/api/generated/schema.d.ts` | client_drift |
| `modules.<name>.enabled` | `true` | runner |
| `modules.<name>.options` | per-module | see below |

Custom config path:

```bash
uv run python -m harness.runner --config /path/to/harness.config.json
```

---

## Module reference

### `client_drift`

**Question answered:** Has the backend OpenAPI moved ahead of the committed
frontend types?

| | |
|-|-|
| Live | `api_v1.openapi()` operation set (`METHOD /path`) |
| Committed | Parsed from `schema.d.ts` (ignores `method?: never` stubs) |
| ERROR | Ops in live OpenAPI missing from committed schema |
| WARN | Ops in committed schema absent from live OpenAPI |

**Fix (ERROR):**

```bash
docker compose up -d    # API must serve /v1/openapi.json
cd frontend && npm run gen:api
git add src/api/generated/schema.d.ts
```

---

### `parity`

**Question answered:** Does the declared feature inventory match what exists in
service / API / CLI / frontend code?

| Layer | Source | Contract |
|-------|--------|----------|
| Service | `src/core/services/*_service.py` | `tests/parity/manifest.py` |
| API tag | FastAPI router tags | manifest |
| CLI group | Click groups | manifest |
| FE route | `frontend/src/App.tsx` routes | manifest `fe_routes` |
| FE API prefix | `/api/<tag>` refs in frontend src | manifest `fe_api_prefixes` |

Also enforced by `make parity` (pytest). When parity fails, add or update a row
in `tests/parity/manifest.py` — same ratchet pattern as service↔API↔CLI.

**Fix (undeclared):** add a manifest row classifying the new surface.  
**Fix (missing):** wire the layer or remove the stale manifest row.

---

### `red`

**Question answered:** Are any API endpoints showing elevated errors or latency?

| Option | Default | Description |
|--------|---------|-------------|
| `source` | `in-process` | Read `MetricsTracker` directly |
| `source` | `http` | GET `{api_base_url}/v1/api/utility/metrics?summary=false` |
| `error_rate_warn` | `0.05` | WARN if failed/total exceeds this |
| `p95_ms_warn` | `2000` | WARN if p95 latency (ms) exceeds this |
| `min_requests` | `1` | Minimum samples before judging an endpoint |

**Cloud example** — set in `harness.config.json`:

```json
"red": {
  "enabled": true,
  "options": {
    "source": "http",
    "metrics_path": "/v1/api/utility/metrics",
    "error_rate_warn": 0.05,
    "p95_ms_warn": 2000
  }
}
```

With no traffic, RED reports **clean** (expected in stealth mode).

---

### `synthetic_smoke`

**Question answered:** Do real-api UI journeys pass against a live backend?

| Option | Default | Description |
|--------|---------|-------------|
| `lane` | `real-api` | Playwright project name |
| `journey_specs` | see config | E2e spec files (real-api-safe load checks) |
| `skip_if_unreachable` | `true` | Skip when `api_health_url` is down |
| `skip_if_playwright_unavailable` | `true` | Skip when Chromium cannot launch |
| `timeout_seconds` | `300` | Subprocess timeout |

Default journeys exercise page-load checks on home, dashboard, OKH catalog,
match, and network — tests that **do not** assert fixture-specific data on the
real-api lane.

**Fix (failures):** read Playwright JSON evidence in `--json` output; run the
same specs directly:

```bash
cd frontend && npm run e2e:real -- e2e/smoke.spec.ts
```

**Force run** (fail instead of skip when API down): set `skip_if_unreachable: false`.

---

## Recommended operating rhythms

### Local dev (quick)

```bash
make harness --modules client_drift,parity   # no servers needed
```

Or full harness; smoke skips if API/browser absent.

### Pre-deploy / cloud staging

```bash
docker compose up -d
make frontend-setup
make harness
```

### CI (future)

```bash
uv run python -m harness.runner --json > harness-report.json
# Gate on .ok == true; archive JSON for triage bot
```

Not yet wired into `make ready` — intentional while loops stabilize.

---

## Architecture

```
harness.config.json
harness/
  protocol.py          Finding, LoopModule, LoopReport
  config.py            load harness.config.json
  base.py              discover → observe → judge → report
  runner.py            CLI entry (python -m harness.runner)
  modules/
    client_drift.py    OpenAPI ↔ schema.d.ts
    parity.py          manifest inventory diff
    red.py             RED threshold judge
    red_metrics.py     metrics load + parse helpers
    synthetic_smoke.py Playwright orchestration
    smoke_runner.py    health checks, playwright invoke, JSON parse
```

Each module implements the same tick:

1. **discover** — static catalog
2. **observe** — live signals / diffs
3. **judge** → `Finding` list (`bug` | `perf` | `gap`)
4. **report** — `LoopReport` with `ok` boolean

---

## Tests

```bash
uv run pytest tests/unit/test_harness.py tests/unit/test_client_drift.py \
  tests/unit/test_parity_loop.py tests/unit/test_red_loop.py \
  tests/unit/test_synthetic_smoke_loop.py -q
uv run pytest tests/parity -q   # manifest ratchet (includes FE layers)
```

---

## Related paths

| Path | Role |
|------|------|
| [`harness/README.md`](../../harness/README.md) | Short dev-oriented overview |
| [`frontend/harness/README.md`](../../frontend/harness/README.md) | UI **build** gate (`make frontend-ready`) |
| [`tests/parity/manifest.py`](../../tests/parity/manifest.py) | Parity contract (single source of truth) |
| [`frontend/e2e/`](../../frontend/e2e/) | Playwright specs consumed by synthetic_smoke |
| [`docs/testing/harness-standards.md`](harness-standards.md) | General pytest lane standards |

---

## Production probes (ACA pain points)

Four **opt-in** probes target issues seen on Azure Container Apps after the
first cloud UI deployment. They are disabled in the default
`harness.config.json` so `make harness` runs verification loops only.

| Probe | Detects |
|-------|---------|
| `probe_match` | Repeated POST `/match` 503 rate, empty error bodies |
| `probe_latency` | Hot-path latency vs configurable warn/error SLOs |
| `probe_cache` | `@cache_response` coverage + double-GET cache effectiveness |
| `probe_okh_files` | Relative file paths / broken external URLs in OKH detail |

```bash
# Enable probes in harness.config.json, point URLs at staging, then:
make harness-probes
```

ERROR findings can auto-generate draft fix proposals under `docs/proposals/`
(`--write-proposals`). Full workflow:
**[probe-workflow.md](probe-workflow.md)**.

---

## Future work

- Wire `make harness` into CI with JSON artifact upload
- Map `Finding.suggested_state` → issue tracker (triage bot)
- Cloud `harness.config.json` overlay pointing at staging URLs
- Expand synthetic journeys as real-api coverage grows
- ~~Implement approved probe proposals (match init, shared cache, file proxy)~~ — match (#270) and cache (#271) **done**; file proxy ([#272](https://github.com/helpfulengineering/supply-graph-ai/issues/272)) **remaining**
- Codify ACA Gunicorn defaults in release deploy (landed in `production.toml`; confirm on next tag)
- Optional: dedicated latency work if `probe_latency` warnings persist on `okh_list`
