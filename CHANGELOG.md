# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.9] - 2026-07-08

### Added

- **Unified distributed cache (#271):** pluggable `CacheBackend` with `memory` (default) and `redis` backends; shared by `@cache_response` and `cached()`; cache stats on `GET /v1/api/utility/metrics`. Optional Redis service in `docker compose --profile redis`.
- **ACA triage harness and production probes:** `make harness` / `make harness-probes` with `probe_match`, `probe_cache`, `probe_okh_files`, and `probe_latency`; proposal workflow under `docs/testing/probe-workflow.md`.

### Fixed

- **Match 503 cold start on ACA (#270):** `MATCHING_EAGER_INIT` pre-loads `MatchingService` during app lifespan; `/health/readiness` reports `matching_service`; frontend surfaces API `request_id` on match errors.
- **Release workflow:** backend deploy verify tolerates ACA cold-start; frontend publish waits on backend tests; changelog gate for tagged releases.

## [0.8.8] - 2026-07-07

### Changed

- **`OKW_SOURCE` unset now defaults to `union` (storage ∪ Maps of Making), not storage.** A match with no configured source is no longer silently limited to blob storage — it draws candidates from both the configured storage backend and the MoM network. `OKW_SOURCE=storage` restricts to blob only and `OKW_SOURCE=mom` to MoM only; `MATCHING_LOCAL_OKW_JSON_DIR` still yields a storage-only local pool (never unioned). Precedence: the environment sets the candidate universe and a per-request override may narrow within it but never broaden it. `okw_source_resolved` now distinguishes unset (→ union) from an explicit `storage`.
- **One shared facility-pool resolver for API and CLI.** `POST /v1/api/match` and the `ohm match` CLI now resolve the candidate pool through a single `OKWService.resolve_match_facilities` (structural parity, not copy-paste), which routes every source through the network surface (`get_network_match_facilities`). MoM candidate loading degrades gracefully — when MoM is unavailable, `union` still returns the storage pool. Facilities without map coordinates are retained for matching (they are only dropped from the map/browse surface).

## [0.8.7] - 2026-07-06

### Added

- **Typed configuration schema + per-environment files (config Slice 1):** a `pydantic-settings` schema (`src/config/schema.py`) is now the single source of truth for the storage target (provider / account / container), the runtime `environment`, `OKW_SOURCE`, and CORS. Non-secret values are checked in per environment at `config/environments/{development,test,production}.toml` and layered under process env vars (env wins); secrets (`AZURE_STORAGE_KEY`, `API_KEYS`, `LLM_*`) stay env/`secretRef`-only. `settings.py` and `storage_config.py` consumers read the schema; the old inline env-read paths were removed. Behaviour-preserving — the `docker --env-file` quote-stripping quirk is consolidated into one normalizing env source, and characterization tests pin per-setting equivalence.
- **Generated `env.template` + staleness gate:** `scripts/generate_env_template.py` emits the schema-owned settings into a marked block of `env.template` (name, default, secret-vs-not). `make env-template` regenerates it (part of `make format`), and a CI step + unit test fail if the committed block drifts from the schema — the lockfile pattern already used for the repository map.
- **Config drift guards (startup posture + `/health` fingerprint + deploy gate):** the app now validates its config at startup — hard-failing in `production` on invalid/missing storage config, warning and degrading elsewhere. Public `/health` gains a best-effort, time-boxed `storage` fingerprint (resolved provider / account / container + `okh/`/`okw/` object counts) so config/data drift is visible. The release workflow's post-deploy step asserts the live container matches `config/environments/production.toml` and that counts are non-zero — an empty or mis-pointed prod container fails the deploy (this is exactly the drift that caused the live zero-match).

### Changed

- **Deploy pipeline now applies the non-secret storage target from the repo.** `deploy/scripts/deploy_azure.py` previously only set `ENVIRONMENT` + `CORS_ORIGINS` and left `STORAGE_*` configured directly on the container app (invisible to the repo — the drift that caused live zero-match). It now authoritatively applies every non-secret value from `config/environments/<environment>.toml` (incl. `AZURE_STORAGE_CONTAINER`) via additive `--set-env-vars`. Secrets are refused by `deploy_env_vars()` and existing `secretRef`s (e.g. `AZURE_STORAGE_KEY`) are left untouched.

## [0.8.6] - 2026-06-30

### Fixed

- **MoM `OKW_SOURCE=mom` silently overridden by `MATCHING_LOCAL_OKW_JSON_DIR`:** `POST /v1/api/match` checked the local-dev JSON directory override before `OKW_SOURCE`, so an explicit request to use the Maps of Making SPARQL bridge as the facility source was silently ignored whenever that dev-convenience env var was set — a divergence from the CLI's `--okw-source mom`, which always reached MoM. `OKW_SOURCE` is now checked first in `_get_filtered_facilities`.
- **CORS preflight 400 on deployed containers:** `CORS_ORIGINS` defaults to an empty list (deny all) in production when unset, which makes Starlette's `CORSMiddleware` reject every browser CORS preflight with 400 before the request reaches a route handler. None of the GCP/AWS/Azure deployment config paths (`deployment.yaml` via `from_dict()`, or the `deploy_gcp.py` CLI script via `with_defaults()`) ever set it. All deployment config construction paths now default `CORS_ORIGINS` to `"*"` (supply-graph-ai is a public API) unless explicitly overridden.

### Added

- **MoM integration documentation and test coverage:** `docs/runbooks/mom-integration-e2e-validation.md` — CLI/API demo runbook verified against the live MoM SPARQL endpoint, plus unit tests for `mom_bridge.py`, taxonomy `wikidata_qid` lookups, and `OKW_SOURCE` routing (none existed since the integration shipped in `#181`).

[0.8.9]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.8...v0.8.9
[0.8.8]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.7...v0.8.8
[0.8.7]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.6...v0.8.7
[0.8.6]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.5...v0.8.6

## [0.8.5] - 2026-06-29

### Fixed

- **`GET /v1/api/okh` timeout:** `SmartFileDiscovery.discover_files()` cascaded to full-bucket strategies (metadata scan, content-validation) when the `okh/` prefix listing returned an empty list, causing it to download every blob in the Azure container. The cascade now only advances when a strategy raises an exception (storage unavailable); an empty result is treated as authoritative and stops the search immediately. `_discover_by_directory_structure` re-raises storage exceptions so the caller can make the cascade decision correctly.

[0.8.5]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.4...v0.8.5

## [0.8.4] - 2026-06-25

### Added

- **Repair workflow epic (GAPs 1–8):** End-to-end API and CLI surface for field-device repair workflows — `AssetRecord` physical-state domain object, `AssetStatus` lifecycle field, repair document extraction pipeline, parts harvesting (`POST /v1/api/asset/harvest-parts`), triage checklist (`POST /v1/api/asset/triage-checklist`), triage report with per-component action recommendations, salvage matching (fleet query for harvestable components), sourcing resolution (`POST /v1/api/asset/resolve-sourcing`), repair-doc import with conservative merge semantics (GAP-4), cross-manifest compatibility via `compatible_manifest_ids` (GAP-8), and claim/reservation mechanism for harvestable components (GAP-7).
- **`make ready` gate:** Single command (`make ready`) that enforces format, lint, unit tests, service↔API↔CLI parity, docs validation, and live E2E as a pre-merge gate. Individual targets: `make parity`, `make validate-docs`, `make e2e`.

### Fixed

- **Azure Container Apps redirect scheme:** Gunicorn was not configured to trust `X-Forwarded-Proto` from ACA's TLS-terminating ingress, causing all trailing-slash redirects to generate `http://` URLs instead of `https://`. Added `forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")` to `gunicorn.conf.py`.
- **`make ready` / parity gate:** Wired `validate-docs`, `parity`, and `e2e` targets into the project Makefile; `make parity` runs `tests/parity` to catch service↔route↔CLI drift early.

[0.8.4]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.3...v0.8.4

## [0.8.3] - 2026-06-20

### Added

- **OKH field presence and completeness metadata** (`#171`): validation output now includes a per-field coverage report.
- **Geographic facility filtering** (`#172`): OKW search accepts `country`, `region`, and `city` query parameters.
- **`Component` data model** (`#173`): structured sub-component references inside OKH manifests.
- **User-driven version pinning** (`#174`): `POST /v1/api/package/pin` locks a package to a specific OKH version.
- **Cryptographic package signing** (`#175`): packages can be signed via federation identity; signature verified on import.
- **OKH bulk import/export** (`#176`): `POST /v1/api/okh/import-collection` and `GET /v1/api/okh/export-collection` for manual collection sync.
- **Setup skill:** `.claude/skills/setup/SKILL.md` — natural-language onboarding wizard for OHM configuration.

[0.8.3]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.2...v0.8.3

## [0.8.2] - 2026-06-04

### Fixed

- **Docker `--env-file` breaks remote storage (quoted env values):** `docker run --env-file` passes values verbatim including surrounding quotes, while `docker-compose` / `python-dotenv` strips them. The `_env()` helper in `storage_config.py` now defensively strips `"` and `'` from all credential and bucket-name variables, preventing DNS failures such as `Cannot connect to host '"myaccount"'.blob.core.windows.net`.
- **Azure Key Vault init noise on every command:** The secrets manager incorrectly detected an Azure Key Vault environment whenever `AZURE_STORAGE_ACCOUNT` was present in `.env`, triggering a noisy warning about missing optional packages on every CLI invocation. Detection now requires `AZURE_KEY_VAULT_URL` or `WEBSITE_INSTANCE_ID` to be set.
- **Blank `"Unexpected error: "` message:** `APIClient.request()`'s catch-all exception handler now always includes the exception type in the message (`Unexpected error (ExcType): detail`), so errors can never silently produce an empty description.

### Documentation

- `README.md` and `docs/development/container-guide.md` updated with explicit `docker run --env-file` guidance, per-provider env-var tables, and a troubleshooting section on the quoted-value DNS failure.

[0.8.2]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.1...v0.8.2

## [0.8.1] - 2026-06-04

### Fixed

- **OKH parser:** `OKHManifest.from_dict` now accepts plain strings in `making_instructions`, `design_files`, `manufacturing_files`, `operating_instructions`, `technical_specifications`, and `publications` — converting them to `DocumentRef` objects with a field-appropriate `DocumentationType`. Previously, string items crashed with `AttributeError: 'str' object has no attribute 'get'`, producing an opaque error in both `ohm okh validate` and `ohm okh fix`.
- **OKH parser:** `standards_used` now accepts plain strings (e.g. `"CC0-1.0"`) in addition to dicts, coercing them to `Standard(standard_title=<string>)`.
- **Codebase:** Removed ~100 redundant inline section comments (`# Required fields first`, `# Optional fields after`, etc.) from API model files; moved module-level imports that were deferred inside methods; simplified `validate_input` in `MatchRequest` from 9 repeated `if x is not None` branches to two list comprehensions; removed dead conditional in `cleanup_service._detect_broken_links` where both branches were identical; removed commented-out dead code from `settings.py`.

### Added

- **Characterization tests:** 138 new unit tests covering `CapabilityRule`, `CapabilityRuleSet`, `CapabilityRuleManager`, `CapabilityMatcher`, `BaseMatchingLayer` utilities, `DirectMatcher`, and `HeuristicMatcher` — raising coverage on those modules from 10–42% to 78–96%.

[0.8.1]: https://github.com/helpfulengineering/supply-graph-ai/compare/v0.8.0...v0.8.1

## [0.8.0] - 2026-06-04

### Added

- **Federation MVP (opt-in):** LAN peer catalog sync via HTTP (`/v1/api/federation/*`), mDNS discovery, follow allowlist, and anti-entropy Merkle sync. Disabled by default (`OHM_FEDERATION_ENABLED=false`). See [federation MVP ADR](docs/architecture/federation-mvp-adr.md).
- **Release automation:** GitHub Actions `Release` workflow validates git tags against `pyproject.toml`, runs pre-release tests, and publishes Docker images to Docker Hub.
- **Release tooling:** `scripts/bump_version.py`, `scripts/validate_release_version.py`.
- **Test harness:** Path-based pytest lane markers in `tests/conftest.py`; contract stability guardrail suite.

### Changed

- **Version:** Application release `0.8.0` (pre-1.0 stable). Single runtime version via `get_version()` / `pyproject.toml`.
- **Docker image:** Built from frozen `uv.lock` (aligned with CI). Published as `touchthesun/openhardwaremanager` with tags `0.8.0`, `0.8`, and `latest`. Multi-arch manifest (`linux/amd64`, `linux/arm64`) via `docker buildx`.
- **Dependencies:** Security-pinned transitive deps (FastAPI ≥0.120, Starlette, urllib3, idna, gitpython, aiohttp); `pip-audit` in CI and release workflows.
- **CI:** Docker build-test on `main` push; `develop` branch name fixed to `dev`; GitHub Actions upgraded to Node.js 24–compatible action majors.

### Fixed

- Contract test lane no longer runs live package-download integration tests (requires `RUN_LIVE_API_TESTS=1`).
- Package download route tests no longer stub `matching` in a way that breaks other unit tests.

[0.8.0]: https://github.com/helpfulengineering/supply-graph-ai/releases/tag/v0.8.0
