# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
