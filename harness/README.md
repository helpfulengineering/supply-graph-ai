# Triage harness (developer overview)

Post-deploy verification loops for OHM. For **how to run, configure, and fix
findings**, see the operator reference:

**[docs/testing/triage-harness.md](../docs/testing/triage-harness.md)**

## Quick start

```bash
make harness                                    # verification loops only
make harness-probes                             # production probes + proposals
uv run python -m harness.runner --modules red   # one loop
uv run python -m harness.runner --probes        # all probes
uv run python -m harness.runner --json          # machine-readable
```

## Loops (all online)

| Module | Signal |
|--------|--------|
| `client_drift` | Live OpenAPI vs committed `schema.d.ts` |
| `parity` | Service ↔ API ↔ CLI ↔ FE inventory |
| `red` | Rate / Errors / Duration thresholds |
| `synthetic_smoke` | Playwright real-api UI journeys |

## Production probes (opt-in)

| Module | Pain point |
|--------|------------|
| `probe_match` | Intermittent match 503 |
| `probe_latency` | Slow hot-path SLO breaches |
| `probe_cache` | Missing / ineffective read cache |
| `probe_okh_files` | OKH file refs not proxied / broken |

See **[docs/testing/probe-workflow.md](../docs/testing/probe-workflow.md)**.

## Layout

```
harness.config.json
harness/
  protocol.py / config.py / base.py / runner.py
  probes/{http,okh,proposal,base}.py
  modules/{client_drift,parity,red,synthetic_smoke,probe_*}.py
docs/proposals/          # auto-generated fix stubs (--write-proposals)
```

Not a merge gate — see `make ready` and `make frontend-ready`.
