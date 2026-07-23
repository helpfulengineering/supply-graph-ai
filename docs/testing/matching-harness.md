# Matching correctness harness

Deterministic tests that prove **valid matches are found** for simple designs
(especially single-process 3D printing), including the Match UI path that
selects Maps of Making spaces by IRI.

## Quick run

```bash
make match-harness
# equivalent:
uv run pytest tests/matching -q
```

Included in `make test` / `make ready` (merge gate). Use `make match-harness`
on the release checklist for a focused signal.

## What it covers

| Case | Location | Expect |
|------|----------|--------|
| MoM IRI `okw_ids` keeps stub in pool | `test_network_okw_ids_mom.py` | pool + ≥1 solution |
| Local 3DP-only → additive OKW | `test_golden_3dp.py` | ≥1 solution |
| MoM mock + IRI selection | `test_golden_3dp.py` | ≥1 solution |
| Local ∪ MoM, no id subset | `test_golden_3dp.py` | ≥1 solution |
| Multi-process vs 3DP-only MoM | `test_golden_3dp.py` | 0 solutions (combinations off) |
| Taxonomy coverage (all processes.yaml) | `test_taxonomy_coverage.py` | report; soft gate |

Fixtures live under [`tests/matching/fixtures/`](../../tests/matching/fixtures/).
MoM is **mocked** in CI (no SPARQL).

## Id alignment (regression)

Browse/network cards use MoM **space IRIs**. Match stubs use a stable
`uuid5(NAMESPACE_URL, iri)` as `ManufacturingFacility.id`. Network match
filters `okw_ids` against the **space id** (IRI or local UUID), not the stub
UUID5. See `OKWService.get_network_match_facilities(..., okw_ids=...)`.

## Adding a golden case

1. Add minimal OKH/OKW (or MoM space) JSON under `tests/matching/fixtures/`.
2. Prefer **single-process** designs when asserting “must find a match”.
3. Parametrize or add a named test in `test_golden_3dp.py`.
4. Run `make match-harness`.

## Taxonomy coverage (all processes.yaml ids)

Scores every canonical manufacturing process against a facility pool and
reports which are matchable vs not. Useful for MoM tag gaps — many processes
will not match; that is expected.

```bash
# Offline (mocked MoM fixtures) — always in make match-harness
uv run pytest tests/matching/test_taxonomy_coverage.py::test_taxonomy_coverage_offline_mocked_mom -s

# Live MoM ∪ local — informational report
MOM_LIVE=1 uv run pytest tests/matching/test_taxonomy_coverage.py::test_taxonomy_coverage_live_mom -s
```

JSON artifacts land under `tests/matching/artifacts/` (gitignored).

## Opt-in live MoM

```bash
MOM_LIVE=1 make match-harness
# or:
MOM_LIVE=1 uv run pytest tests/matching -m mom_live -s
```

Skipped unless `MOM_LIVE=1`. Hits live SPARQL; asserts a non-empty MoM pool
with at least one space whose processes normalize toward 3D printing, a soft
network match with `facility_count > 0`, and prints full taxonomy coverage.

Recommended before cutting a release that touches matching or MoM.

## Related

- [WF-1: Single-level matching](workflows/wf01-single-level-matching.md)
- [`scripts/matching_batch.py`](../../scripts/matching_batch.py) — storage-only batch eval (separate from this harness)
- Probe `probe_match` — availability/503, not correctness
