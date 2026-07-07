# Conference demo readiness tracker

**Purpose:** Living progress tracker for public-demo documentation sync and targeted Python documentation/typing work. Code and OpenAPI are the source of truth; narrative docs follow.

**Last updated:** 2026-04-29 (Track B Wave B3 follow-up: StorageService + OKH/OKW service docstrings/type-hint sync)

---

## Goal and scope

**Must have before the conference**

- README quick start matches real ports, compose service names, and `/v1` doc URLs.
- API overview pages do not state incorrect route or router counts; readers are pointed to interactive OpenAPI docs for the full contract.
- CLI docs describe commands that exist in `src/cli/main.py` (installation story aligned with README: Docker + `uv` as primary).

**Should have**

- Demo-path workflows in `docs/testing/workflows/` spot-checked against current behavior.
- Docstrings and type hints improved on the highest-visibility surfaces (`src/core/api/`, `src/cli/`, core services used in the demo script).

Progress for both items lives in [**Should have backlog**](#should-have-backlog) below (updated as each slice is finished).

**Nice to have (defer if timeboxed)**

- Repo-wide Ruff `D*` / `ANN` or mypy strictness (large change; not required for demo day).

---

## Milestone timeline

| Week | Checkpoint |
|------|------------|
| **Week 1** | P0 doc audit complete (README, compose, `docs/api/*` intro); CLI install + command list aligned with `ohm --help`; tracker audit log updated. |
| **Week 2** | P1 workflow spot-checks; demo-path code inventory rows marked done or explicitly deferred; `mkdocs build` clean; optional CI snippet for OpenAPI export documented here. |

---

## Workstreams

1. **Documentation sync** — Compare MkDocs and README to code; fix or trim stale claims; prefer linking to `/v1/docs` and `/v1/openapi.json` over duplicating endpoint lists.
2. **Python docstrings and types** — Google-style docstrings and explicit hints on public handlers and demo-critical services; incremental PRs.
3. **Optional tooling** — `scripts/dump_api_routes.py` dumps sorted `METHOD path` lines (or `--count-only`). `scripts/generate_openapi_routes_md.py` writes the MkDocs route table. Strict MkDocs link checking remains optional.

---

## Should have backlog

Use this section as the working checklist for **Should have** items in [Goal and scope](#goal-and-scope). Update rows and checkboxes when a slice is finished.

### Track A: Demo-path workflows {: #track-a-workflows }

**Goal:** Every workflow doc is either verified against current code or explicitly flagged; readers are never told fictional automation exists in this repository.

| WF | Spec vs `src/` (spot-check) | Mapped tests on this branch |
|----|------------------------------|-------------------------------|
| [WF-1](../testing/workflows/wf01-single-level-matching.md) | `OKHManifest.extract_requirements()` → `ProcessRequirement` (`src/core/models/okh.py`); `MatchingService.find_matches_with_manifest` → `Set[SupplyTreeSolution]` | Partial: `tests/unit/test_match_coverage.py` exercises `_build_match_summary` / process coverage (not the full matching pipeline). |
| [WF-2](../testing/workflows/wf02-nested-bom-matching.md) | `BOMResolutionService._detect_bom_type`, `explode_bom`; `MatchingService.match_with_nested_components` | None dedicated. |
| [WF-3](../testing/workflows/wf03-okh-generation-from-url.md) | OKH generation stack reachable via CLI/API (`OKHService`, generation routes) | None dedicated. |
| [WF-4](../testing/workflows/wf04-quality-tiered-validation.md) | `ValidationContext` / validators wired from API (`src/core/validation/`) | None dedicated. |
| [WF-5](../testing/workflows/wf05-datasheet-round-trip.md) | `DatasheetConverter` + `/v1/api/convert/*` | None dedicated. |
| [WF-6](../testing/workflows/wf06-error-recovery.md) | Uses same matching entrypoints as WF-1; error shapes via API handlers | None dedicated. |
| [WF-7](../testing/workflows/wf07-solution-lifecycle.md) | `StorageService` solution persistence APIs (`save_supply_tree_solution`, `load_*`, `list_*`, TTL/stale/cleanup, `delete_*`) | Partial: `tests/performance/test_supply_tree_performance.py` stresses `SupplyTree` / `SupplyTreeSolution` models (not storage lifecycle). |

**Repository layout:** The [`docs/testing/workflows/README.md`](../testing/workflows/README.md) **target** tree `tests/e2e/test_wf*.py` is not present on the default branch as of 2026-04-30. Commands in that README apply once that package exists or is ported.

- [x] **Track A — README honesty:** Workflow index and “Related issues” no longer claim all WF E2E suites live under `tests/e2e/` on this branch.
- [x] **Track A — Entrypoint pass:** Table above records a code-side spot-check for WF-1–WF-7.
- [ ] **Track A — Automation (optional stretch):** Add `tests/e2e/` (or per-WF files under `tests/integration/`) and replace “None dedicated” rows with real modules.

### Track B: Docstrings and types (demo bar) {: #track-b-docstrings-types }

Work the [Code quality inventory](#code-quality-inventory) top-down; tick rows here when a wave meets the agreed bar for touched modules.

| Wave | Scope | Status |
|------|--------|--------|
| B1 | `src/core/api/routes/*.py` public handlers + shared `error_handlers` / `decorators` | **done** (2026-04-30): `error_handlers` uses `Optional`/`Any` correctly; route modules have explicit return types on public handlers (concrete types where safe with FastAPI inference, `Any` on large OKH/OKW/package/supply-tree surfaces); `convert`, `rules`, `match` hot paths tightened; `utility` module doc + handler returns. |
| B2 | `src/cli/` (`main.py` already improved; then `match`, `okh`, `okw`, `package`, `solution`, …) | **done** (2026-04-30): `base.py` / `cli/decorators.py` typed; all `@click.group` handlers `-> None`; `solution.py` commands use `Context` + `-> None`; OKH/OKW/package manifest readers `dict[str, Any]`; plus optional **B2.1** focused `match.py` pass (`ctx: Context`, `-> None` on commands, typed helper returns). |
| B3 | Demo-path services (`matching_service.py`, `storage_service.py`, `okh_service.py`, `okw_service.py`, …) | **done** (2026-04-29): Google-style ``Args``/``Returns``/``Raises`` on primary matching/storage/OKH/OKW entrypoints; ``find_matches`` empty branch returns ``set()``; typed storage load/save surfaces (including ``load_supply_tree_solution_with_metadata``); service ``__init__`` ``-> None``; follow-up pass covered `DomainStorageHandler`/`StorageRegistry` and OKH/OKW validation + LLM helper method docs. |

**Convention reminder:** Google-style docstrings; explicit type hints on public handlers and service methods the demo touches.

---

## Environment story (canonical for external readers)

| Audience | Primary path | Notes |
|----------|----------------|-------|
| Conference attendees / new contributors | **Docker Compose** for API + **`uv`** for CLI, tests, MkDocs | Documented in [README.md](../../README.md). |
| CI / automation | **`uv sync`** + **`uv run …`** | See [.github/workflows/ci-cd.yml](../../.github/workflows/ci-cd.yml). |

---

## Documentation audit log

| Priority | Document | Status | Notes | PR |
|----------|----------|--------|-------|-----|
| P0 | [README.md](../../README.md) | reviewed | Ports `8001`, `/v1/docs`, compose service `ohm-api` match [docker-compose.yml](../../docker-compose.yml) and [src/core/main.py](../../src/core/main.py) (`api_v1` mounted at `/v1`). Fixed typo: "dependenciesif" → "dependencies (if". | — |
| P0 | [docker-compose.yml](../../docker-compose.yml) | reviewed | Host `8001:8001`, healthcheck `localhost:8001/health`. | — |
| P0 | [docs/api/routes.md](../api/routes.md) | updated | **Option C:** hand-maintained per-route encyclopedia removed; `docs/api/_generated/openapi-route-table.md` is generated by `scripts/generate_openapi_routes_md.py` and included via MkDocs snippets. Narrative (errors, patterns, examples) kept; duplicate **Implementation Status** list removed. Stub `###` headings preserve cheatsheet deep-link anchors. | — |
| P0 | [docs/api/index.md](../api/index.md) | updated | Replaced incorrect "43 routes / 6 command groups" with accurate summary. | — |
| P1 | [docs/CLI/index.md](../CLI/index.md) | updated | Prerequisites and command groups aligned with `ohm --help`; `supply-tree` placeholder replaced with `solution` commands. | — |
| P1 | [docs/CLI/examples.md](../CLI/examples.md) | updated | Supply tree subsection replaced with `solution` examples. | — |
| P1 | [docs/CLI/quick-start.md](../CLI/quick-start.md) | updated | Primary install path uses `uv` + `docker compose`; optional pip-only venv note for edge cases. | — |
| P1 | Demo workflows under `docs/testing/workflows/` | updated | **Track A (2026-04-30):** README index + issues/progress log aligned with repo: `tests/e2e/` is **target only** (not on branch); per-WF service/API names spot-checked vs `src/`. Partial test mapping documented. See [Should have backlog — Track A](#track-a-workflows). | — |
| P2 | Architecture pages under `docs/architecture/` | reviewed | `architecture/index.md`: admonition added for stale `ome.*` snippets vs `src.core.*`; use `.repo-map.md` for structure. | — |
| P1 | OME → OHM branding sweep | updated | Replaced legacy **Open Matching Engine** / `ome` CLI / `open-matching-engine` image names in docs, logging namespaces (`ohm.llm.*`), default `SERVICE_NAME` (`ohm-api`), storage scripts, and unit-test imports. Regenerate [.repo-map.md](../../.repo-map.md) after pull. | — |
| P1 | Conda / pip → **uv** documentation | updated | Developer guide, local setup, runbooks, GCP doc, CLI examples/architecture, scaffolding MkDocs, CONTRIBUTING, `.cursorrules` / `.cursor/rules/ohm-rules.mdc`, script docstrings, and **CI** (`.github/workflows/ci-cd.yml`) now describe `uv sync` / `uv run`. | — |

---

## Branding: Open Matching Engine (OME) → Open Hardware Manager (OHM)

The product and CLI are **OHM** / **`ohm`**. Legacy names to eliminate in new work:

| Legacy | Replace with |
|--------|----------------|
| Open Matching Engine | Open Hardware Manager |
| `ome` CLI prefix (`ome llm`, …) | `ohm …` |
| Docker image / service name `open-matching-engine` | Repository image name `supply-graph-ai` (or your registry tag); compose service `ohm-api` |
| Log namespace `ome.llm` / `ome.performance` / `ome.audit` | `ohm.llm` / `ohm.performance` / `ohm.audit` |
| JSON log field default `open-matching-engine` | `ohm-api` (override with `SERVICE_NAME`) |
| Fictional Python package `ome.*` in architecture drafts | `src.core.*` (see repo map) |

Azure **blob container** names are deployment-specific; defaults in tooling now use **`ohm`** with a note that older environments may still use **`ome`**.

---

## Known test, import, and tooling issues (track to resolution)

These were surfaced while aligning docs and running targeted tests. Remove or shrink rows here as each item is fixed and covered by CI.

### 1. Unit test import path (`tests/unit/test_match_coverage.py`)

**Symptom:** `pytest tests/unit/test_match_coverage.py` failed on `from core.api.routes.match import _build_match_summary` (or imported a different `core` than intended).

**Cause:** The repository package layout is **`src.core`**, not a top-level `core` package. Inserting only `…/src` on `sys.path` and importing `core.*` is fragile: another distribution named `core` on `PYTHONPATH` can shadow the project.

**Mitigation applied:** Insert the **repository root** on `sys.path` and use `from src.core.api.routes.match import _build_match_summary`.

**Follow-up:** Audit other tests for `from core.` / `import core` patterns and standardize on `src.core` or `pytest`’s `pythonpath` / editable install conventions. (`tests/performance/test_supply_tree_performance.py` updated in the same pass.)

### 2. Pytest configuration vs global interpreter

**Symptom:** Warnings such as `Unknown config option: timeout` when `pytest` is not the one installed with dev extras.

**Cause:** `pyproject.toml` enables `pytest-timeout` options; a bare `pytest` from another environment ignores unknown keys.

**Mitigation:** Prefer `uv run pytest …` after `uv sync --extra dev` so pytest and plugins match `pyproject.toml`.

### 3. `uv run pytest` without dev extras picked the wrong `pytest` binary

**Symptom:** `TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'` when importing `src.core.api.routes.match` during tests — even though `APIRouter` in source is constructed with only `tags` and `responses`.

**Cause:** With only `uv sync` (no **dev** extra), `.venv/bin/pytest` may be **absent**. `uv run pytest` then falls through to a **`pytest` on `PATH`** (for example Conda base). That interpreter loads a **different FastAPI/Starlette pair** than the project’s `.venv`, which can surface as bogus `APIRouter` keyword errors at import time.

**Mitigation:** Run `uv sync --extra dev` so pytest is installed in `.venv`, then `uv run pytest …`. Prefer `uv run python -m pytest …` if you need to be explicit.

**Note:** Importing full `match.py` to unit-test `_build_match_summary` is heavy; a future refactor can move that helper to a small module with no router registration to shorten import chains.

### 4. FastAPI / Starlette version skew (if `on_startup` errors return after fixing §3)

If the wrong-pytest issue is ruled out, compare `uv pip show fastapi starlette` with `pyproject.toml` / `uv.lock` and ensure no second Python on `PYTHONPATH` shadows the project.

### 5. Log and metrics consumers after logger rename

**Change:** `ome.llm` → `ohm.llm` (and performance/audit siblings); structured JSON default `service` field default → `ohm-api`.

**Action:** Update Datadog/GCP log queries, dashboards, or saved filters that still key on `open-matching-engine` or `ome.llm`.

---

## API machine truth (refresh before demo)

Regenerate when routes change:

```bash
uv run python -c "
from src.core.main import api_v1
ops = []
for r in api_v1.routes:
    methods = getattr(r, 'methods', None) or set()
    path = getattr(r, 'path', '')
    for m in sorted(methods):
        if m in ('HEAD', 'OPTIONS'):
            continue
        ops.append(f'{m} {path}')
print(len(ops), 'HTTP operations under mounted api_v1')
"
```

**Snapshot 2026-04-29:** **95** HTTP operations on versioned app routes (GET/POST/PUT/PATCH/DELETE excluding HEAD/OPTIONS). **11** routers mounted under `/v1` in `src/core/main.py`: `match`, `okh`, `okw`, `supply_tree`, `utility`, `package`, `llm`, `rules`, `convert`, `taxonomy`, `rfq`.

Rough counts by second path segment under `/api/` (same snapshot): `supply-tree` 25, `match` 17, `okh` 13, `okw` 11, `package` 10, `utility` 3, `llm` 2, `convert` 2, `taxonomy` 2, `rfq` 1, plus non-`/api/` routes (e.g. health) grouped as remainder.

**Authoritative detail:** With API running, use `http://localhost:8001/v1/docs` and `http://localhost:8001/v1/openapi.json`.

---

## Documentation update process (repeatable)

1. Run the snippet above (or save `/v1/openapi.json` from a running container) before claiming numbers in docs.
2. For large endpoint catalogs: keep **overview + patterns** in MkDocs; do not hand-maintain full path lists unless someone owns ongoing sync.
3. Any PR that adds or changes a route or CLI command updates the relevant doc section and a row in the audit log above.
4. Before the demo: `uv sync --extra docs && uv run mkdocs build`.
5. Optional: `uv run python scripts/dump_api_routes.py` (or `--count-only`) to refresh route counts in release notes or this tracker.

---

## Code quality inventory

**Convention (demo bar)**

- **Docstrings:** Google style for new or touched public modules (summary line, `Args` / `Returns` / `Raises` where useful).
- **Type hints:** Explicit on public functions, route handlers, and service methods on the demo path; follow existing imports (`Optional`, `list[str]`, etc.).

**Current enforcement:** [pyproject.toml](../../pyproject.toml) Ruff `select` is `E9`, `F63`, `F7`, `F82` only — no docstring or annotation rules in CI.

### Wave 1 — `src/core/api/` (highest visibility)

| Area | Docstrings | Type hints | Notes |
|------|------------|------------|-------|
| `routes/*.py` handlers | partial | **improved** (Wave B1) | Public `async` handlers annotated with return types; OKH/OKW/package/supply-tree use explicit `Any` where a precise union would fight `response_model` / `@api_endpoint` wrapping. |
| `models/` (request/response) | partial | strong | Pydantic models carry types; module docstrings vary. |
| `decorators.py`, `error_handlers.py` | partial | **improved** (`error_handlers`) | `error_handlers`: `Optional`/`Any` on shared helpers; async handlers return `JSONResponse`. `decorators.py`: unchanged this pass (factory typing deferred). |

### Wave 2 — `src/cli/`

| Module | Docstrings | Type hints | Notes |
|--------|------------|------------|-------|
| `main.py` | yes | improved | `cli` / `config` use `click.Context`, `CLIContext` cast, `-> None`; Google-style docstring on `cli`. |
| `base.py` | partial | **improved** (B2) | `ensure_domains_registered`, `CLIConfig`/`CLIContext`/`APIClient`/`SmartCommand`/`ServiceFallback` `__init__` and helpers typed; `execute_with_fallback` uses `Awaitable` callables. |
| `decorators.py` (CLI) | partial | **improved** (B2) | `async_command`, composable wrappers, and `cli_command`/`cli_group` factories annotated with `Callable[..., Any]` / `Awaitable`. |
| `solution.py` | yes | **improved** (B2) | All solution subcommands: `ctx: Context`, `-> None`. |
| `match.py`, `okh.py`, `okw.py`, `package.py` | partial | **improved** (B2/B2.1) | Click groups `-> None`; shared `_read_*` helpers return `dict[str, Any]`; `match.py` command callbacks now typed (`ctx: Context`, `-> None`) including rules subcommands. |
| Other groups (`storage`, `utility`, …) | partial | partial | Same group `-> None` pass; deeper per-command typing when touched. |

### Wave 3 — Demo-path services (adjust to your actual demo)

| Module | Docstrings | Type hints | Notes |
|--------|------------|------------|-------|
| `matching_service.py` | **improved** (B3) | **improved** (B3) | Core public methods: ``initialize``, ``find_matches*``, composite matcher, ``get_match_explanation``, ``get_available_domains``, ``ensure_initialized``; nested matcher docstring includes ``manifest_path``. |
| `storage_service.py` | **improved** (B3+) | **improved** (B3+) | Class + ``get_instance``/``__init__``; supply tree and solution save/load typed with ``SupplyTree`` / ``SupplyTreeSolution``; follow-up covers lifecycle/index/backup methods plus `DomainStorageHandler` and `StorageRegistry` docs. |
| `okh_service.py` / `okw_service.py` | **improved** (B3+) | **improved** (B3+) | CRUD/list/fetch entrypoints documented; ``__init__`` ``-> None``; follow-up pass adds explicit doc contracts on update/delete/key lookup/validate/LLM helper methods. |

**Optional metrics (not in CI):** Ruff D/ANN or interrogate on a single package directory to populate counts in a later revision of this table.

---

## Success criteria checklist

- [x] README and compose agree on API port and doc URL.
- [x] `docs/api/routes.md` and `docs/api/index.md` intros do not assert obsolete route/group counts.
- [x] CLI docs list the same command groups as `ohm --help`; no fictional `ohm supply-tree` commands.
- [x] P1 workflow docs spot-checked and audit rows marked `reviewed`.
- [x] Should-have **Track A** (workflows): README + this backlog aligned with repository test layout; per-WF entrypoints spot-checked (2026-04-30).
- [x] Should-have **Track B — Wave B1** (`src/core/api/routes/*`, `error_handlers`): see [backlog](#track-b-docstrings-types).
- [x] Should-have **Track B — Wave B2** (`src/cli/`): see [backlog](#track-b-docstrings-types).
- [x] Should-have **Track B — Wave B3** (demo-path services): primary rows in [backlog](#track-b-docstrings-types) and Wave 3 table under [Code quality inventory](#code-quality-inventory) aligned (2026-04-29).
- [x] Demo-critical inventory rows upgraded toward agreed bar (`src/cli/main.py`, demo-path services); remaining modules incremental.
