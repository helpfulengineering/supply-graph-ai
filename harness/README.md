# Triage harness

Multi-loop post-deploy verification for OHM. Independent loops load as modules;
enable them one at a time as they come online. Does **not** replace
`make ready` or `make frontend-ready` — those remain the merge gates. This
harness is the continuous / on-demand triage surface for cloud deployment.

## Loops

| Module | Signal | Status |
|--------|--------|--------|
| `parity` | Feature inventory: service ↔ API ↔ CLI ↔ (soon) FE routes | stub |
| `red` | Rate / Errors / Duration from API metrics | stub |
| `synthetic_smoke` | Playwright UI journeys against real API | stub |
| `client_drift` | Live OpenAPI vs committed `schema.d.ts` | **online** |

Stubs always report `ok`. Online modules fail the run on error-severity
findings. Today only `client_drift` is online.

## Run

```bash
# All modules
make harness
# or
uv run python -m harness.runner

# Subset
uv run python -m harness.runner --modules parity,client_drift

# Machine-readable
uv run python -m harness.runner --json

# List modules
uv run python -m harness.runner --list
```

## Layout

```
harness.config.json          # enablement, URLs, thresholds
harness/
  protocol.py                # Finding / LoopModule contract
  config.py                  # config loader
  base.py                    # BaseLoopModule (discover→observe→judge→report)
  runner.py                  # CLI
  modules/
    parity.py
    red.py
    synthetic_smoke.py
    client_drift.py
```

## Module contract

Each module implements:

1. **discover** — static inventory (what exists)
2. **observe** — live signals / diffs for this tick
3. **judge** — turn observations into `Finding`s (`bug` | `perf` | `gap`)
4. **run** — full tick → `LoopReport`

Findings carry `suggested_state` (default `needs-triage`) for later issue-tracker
integration.

## Relationship to existing gates

| Concern | Location |
|---------|----------|
| Merge gate (format/lint/tests/parity/docs) | `make ready` |
| Frontend build gate | `make frontend-ready` / `frontend/harness/` |
| Triage loops (this) | `make harness` / `harness/` |
| Service↔API↔CLI ratchet | `tests/parity/` (consumed by `parity` module) |
| RED collection | `RequestTrackingMiddleware` + `MetricsTracker` |
| UI journeys | `frontend/e2e/` (consumed by `synthetic_smoke`) |
| Typed API client | `frontend/harness/gen-api-types.mjs` (watched by `client_drift`) |

## Coming online (build order)

1. Shared protocol + stubs ✓
2. `client_drift` — live OpenAPI vs committed schema ✓
3. `parity` — FE route inventory vs API areas ← next
4. `red` — scrape metrics, apply thresholds from config
5. `synthetic_smoke` — drive Playwright real-api lane as a loop tick

### `client_drift` behaviour

- **Live inventory**: `api_v1.openapi()` in-process (no HTTP server required).
- **Committed inventory**: parse `frontend/src/api/generated/schema.d.ts` for
  implemented `METHOD /path` pairs (`method?: never` stubs ignored).
- **Findings**:
  - ERROR `gap` — ops in live OpenAPI missing from committed schema
    (fix: `cd frontend && npm run gen:api` with API reachable at `openapiUrl`).
  - WARN `gap` — ops in committed schema absent from live OpenAPI.
