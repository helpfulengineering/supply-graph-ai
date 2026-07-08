# Code style and project map via uv-managed environment.
.PHONY: format format-check lint test check black ruff repo-map env-template env-template-check validate-docs version-check lock-check scripts scripts-check parity ready setup verify-env frontend-setup frontend-ready harness harness-probes

# Web frontend verification harness (the frontend analogue of `ready`).
# See frontend/harness/README.md. Runs typecheck, lint, unit, build, and the
# mocked E2E + a11y + screenshots lane; nonzero on any failure.
frontend-ready:
	cd frontend && npm run frontend-ready

# Multi-loop triage harness (parity / RED / synthetic smoke / client drift).
# Modules load independently; stubs report ok until each judge comes online.
# See harness/README.md. Not part of `make ready` (merge gate) yet.
harness:
	uv run python -m harness.runner --loops

# Production probes for Azure ACA pain points (match 503, latency, cache, OKH files).
# Enable probe modules in harness.config.json and point URLs at staging first.
harness-probes:
	uv run python -m harness.runner --probes --write-proposals

# One-step frontend contributor setup: JS deps + Playwright browsers + verify.
# Installs Chromium and the headless shell (both required by @playwright/test).
frontend-setup:
	cd frontend && npm ci
	cd frontend && npx playwright install chromium chromium-headless-shell
	@echo "==> Verifying Playwright can launch headless Chromium..."
	@cd frontend && node -e 'const { chromium } = require("@playwright/test"); chromium.launch({ headless: true }).then(b => b.close()).then(() => console.log("==> Playwright Chromium ready")).catch(e => { console.error("==> Playwright verify FAILED:", e.message); process.exit(1); })'

# One-step contributor setup. Provisions the full uv-managed environment (all
# dependencies incl. the pinned spaCy model) and verifies it is fully online.
# Idempotent — safe to re-run any time to repair/refresh the environment.
setup:
	@command -v uv >/dev/null 2>&1 || { \
	  echo "uv not found. Install it: https://docs.astral.sh/uv/getting-started/installation/"; \
	  exit 1; }
	uv sync --extra dev
	$(MAKE) verify-env

# Fail loudly if a historically fragile dependency is missing or unloadable.
# Pure verification (no mutation), so it is also a step in the `ready` gate.
verify-env:
	uv run python scripts/verify_dev_env.py

format: black ruff repo-map env-template

black:
	uv run black .

ruff:
	uv run ruff check src --fix

format-check:
	uv run black --check .

lint:
	uv run ruff check src

test:
	uv run pytest

check: lint format-check test

repo-map:
	uv run python scripts/generate_repo_map.py

# Regenerate the schema-owned block of env.template from src/config/schema.py.
env-template:
	uv run python scripts/generate_env_template.py

# Staleness gate (lockfile pattern): fails if the generated block is out of date.
env-template-check:
	uv run python scripts/generate_env_template.py --check

validate-docs:
	uv run python scripts/validate_docs.py

# Version drift gate (lockfile pattern): fails if any "current release" claim
# in the registry (scripts/bump_version.py) drifts from pyproject.toml.
version-check:
	uv run python scripts/bump_version.py --check

# Lockfile drift gate: fails if uv.lock is stale vs pyproject.toml. Non-mutating
# (unlike `uv lock`/`uv sync`), so it is safe in the `ready` gate.
lock-check:
	uv lock --check

# Regenerate scripts/README.md from scripts/registry.toml.
scripts:
	uv run python scripts/generate_scripts_index.py

# Script registry gate: fails if a script is unregistered or README is stale.
scripts-check:
	uv run python scripts/generate_scripts_index.py --check

# Service <-> API <-> CLI parity gate. Fails when a service, route, or CLI
# group drifts from the declared contract in tests/parity/manifest.py.
parity:
	uv run pytest tests/parity -q

# Definition of done. Green tests are not "ready to merge"; this is.
# Each step verifies (does not mutate) and fails fast. Run before any MR.
ready:
	@echo "==> [1/9] env verify";      $(MAKE) verify-env
	@echo "==> [2/9] format check";    $(MAKE) format-check
	@echo "==> [3/9] lint";            $(MAKE) lint
	@echo "==> [4/9] unit tests";      $(MAKE) test
	@echo "==> [5/9] service parity";  $(MAKE) parity
	@echo "==> [6/9] docs ↔ code";     $(MAKE) validate-docs
	@echo "==> [7/9] version sync";    $(MAKE) version-check
	@echo "==> [8/9] lockfile sync";   $(MAKE) lock-check
	@echo "==> [9/9] script registry"; $(MAKE) scripts-check
	@echo "==> READY: all gates passed."
