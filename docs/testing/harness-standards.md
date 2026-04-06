# Test Harness Standards

Last updated: 2026-04-06

## Purpose

This document defines the baseline standards for writing and maintaining tests in
this repository so we can prevent hangs, reduce flakiness, and keep CI signal
high.

## Lane Model and Markers

Tests are organized by intent and selected by marker lanes:

- `unit`: deterministic logic tests with no external I/O
- `contract`: API/CLI contract tests with isolated dependencies
- `integration`: cross-component tests that may require seeded data/services
- `e2e`: end-to-end workflow tests
- `benchmark`: performance-focused checks
- `quarantine`: non-blocking tests excluded from default runs
- `allow_network`: explicit opt-out for tests that intentionally need network

Global lane assignment is applied in `tests/conftest.py` by test path so marker
semantics are consistent in local and CI runs.

## Isolation Rules

### API tests

- Do not use production `main.app` in contract tests.
- Use an isolated lightweight app fixture that mounts `api_v1` under `/v1`.
- Keep dependency overrides explicit and local to each test.
- Clear `api_v1.dependency_overrides` in teardown/finally blocks.

### Network usage

- External network is blocked by default for `unit` and `contract` tests.
- If intentional network access is required, mark the test with
  `@pytest.mark.allow_network` and document why in the test body/docstring.

### Singleton/service lifecycle

- API tests rely on `tests/api/conftest.py` autouse fixtures to patch service
  singleton getters and clean singleton state after each test.
- New singleton-backed services must be added to cleanup logic when introduced.

## Timeout and Hang Guardrails

- `pytest-timeout` is required in dev and CI test dependencies.
- Default timeout policy:
  - `timeout = 90`
  - `timeout_method = "thread"`
- Timeout failures automatically include active thread diagnostics via
  `pytest_runtest_makereport` hook in `tests/conftest.py`.

## Fixture and Assertion Practices

- Use context-managed test clients:
  - `with TestClient(app) as test_client: yield test_client`
- Prefer deterministic fixtures and `AsyncMock`/`MagicMock` over real services.
- Avoid sleeps and polling loops in `unit`/`contract` tests.
- Assert contract shape and core semantics, not incidental formatting.

## Local and CI Commands

Recommended local runs:

```bash
# Fast deterministic checks
pytest -m "unit and not quarantine"
pytest -m "contract and not quarantine"

# Integration checks (as needed)
pytest -m "integration and not quarantine"
```

CI runs lanes separately in `.github/workflows/ci-cd.yml`:

- unit lane
- contract lane
- integration lane
- contract stability guardrail suite (focused high-risk API/CLI contract files)

## Maintenance Cadence

Run this lightweight maintenance loop on a fixed cadence:

- Weekly:
  - Review newly added tests for correct marker and lane placement.
  - Ensure API contract tests use isolated mounted app fixtures.
- Bi-weekly:
  - Review `quarantine` inventory and either modernize, promote, or remove stale
    tests.
  - Audit `allow_network` usage and keep exceptions minimal.
- Monthly:
  - Execute a cull/modernization pass for drifted or low-value tests.
  - Re-validate timeout policy and diagnostics usefulness.

## Definition of Done for New Test Work

A test change is complete only when:

- Correct lane marker semantics are preserved.
- No hidden external network or service startup is introduced in
  `unit`/`contract` lanes.
- Fixtures and singleton state are deterministic across test boundaries.
- Relevant lane commands pass locally and in CI.
