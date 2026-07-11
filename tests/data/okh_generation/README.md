# OKH generation quality harness

Supports the scripts under `scripts/okh_generation_*.py`. This package is the
durable entry point for unit metrics, offline baseline scoring, and live canary
batch runs. Process notes for the Materials quality workstream live under
`notes/` (gitignored), not under `docs/`.

## Layout

| Path | Role |
|------|------|
| `repositories.json` | Canary corpus (26 repos) |
| `metrics.py` | `heuristic_manifest_quality` (+ Materials heuristics) |
| `baseline_report.py` | Offline GT comparison |
| `manifest_discovery.py` | URL / slug / path helpers |
| `ground_truth/` | Blocking-field GT (repo-001, repo-002) |
| `fixtures/` | Tiny manifests for unit tests |
| `clones/` | Generated manifests (**gitignored**) |

## Modes

```bash
# A — unit (PR CI)
uv run pytest tests/unit/test_okh_generation_*.py -q

# B — offline score (needs manifests under clones/)
uv run python scripts/okh_generation_baseline_report.py --stdout
uv run python scripts/okh_generation_layer_compare.py --stdout

# C — live canary (optional LLM)
export GITLAB_SELF_HOSTED_HOSTS=gitlab.waag.org   # Waag BioHack repos
uv run python scripts/okh_generation_batch.py \
  --core-only --skip-existing \
  --repo-timeout-seconds 600 \
  --progress-interval-seconds 30

# Phase 5 validation — sequential from-URL regen with before/after Materials tracker
uv run python scripts/okh_generation_materials_regen_compare.py --core-only
# Tracker: tests/data/okh_generation/materials_regen_tracker.json (gitignored)
# After manifests: tests/data/okh_generation/clones-regen/ (gitignored)
```

Batch progress prints `[i/n] id starting|still running|ok|error` on stderr, enforces a
per-repo wall-clock timeout (default 600s), and rewrites `last_batch_report.json`
after every repo so a hang does not lose prior results. Clone failures fall back to
the platform API. Override shallow-clone wait with `OHM_GIT_CLONE_TIMEOUT` (default 300).

Default manifest directory for batch / baseline / layer-compare is
`tests/data/okh_generation/clones/`.

## Materials baseline

Phase 4 canary (2026-07-10) exposed the failure modes. Phase 5 normalize gate
(shape + doc evidence + near-dup) applied offline to those manifests:

| Repo | materials | near-dups | prose-like | score |
|------|-----------|-----------|------------|-------|
| repo-001 (rover) | 5 | 0 | 0 | 1.00 |
| repo-002 (openflexure) | 4 | 0 | 0 | 1.00 |
| repo-012 (iris-case) | 6 | 0 | 0 | 1.00 |
| bha-centrifuge | 0 | 0 | 0 | 1.00 |
| bha-stirrer | 0 | 0 | 0 | 1.00 |
| bha-thermocycler | 0 | 0 | 0 | 1.00 |
| air-quality-sensor… | 12 | 0 | 0 | 1.00 |

**Phase 4 totals (before fix):** 4 near-dup pairs; 66 prose-like rows.
**After Phase 5 filter:** 0 near-dups; 0 prose-like. BHA repos drop to empty
materials when every extracted row was junk (prefer empty over polluted).
Regenerate with batch for live evidence-gate coverage against project docs.
