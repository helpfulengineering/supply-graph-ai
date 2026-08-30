# Code style and project map via uv-managed environment.
#
# Every recipe below shells out to `uv run`, and each one re-resolves the lock
# before it runs. `en_core_web_md` is a direct-URL dependency, so re-resolving
# means asking github.com for the wheel's metadata — 13 times over a `make
# ready`, any one of which can fail the whole gate on a network hiccup that has
# nothing to do with the change under test. Freezing pins every recipe to the
# committed lock, which is what a verification gate should be measuring anyway.
# `lock-check` still runs `uv lock --check`, so a lock that has drifted from
# pyproject.toml is caught there rather than hidden here.
export UV_FROZEN := 1

.PHONY: format format-check lint test check black ruff links-check env-template env-template-check validate-docs version-check lock-check scripts scripts-check demo-world-check parity secrets-check ready setup verify-env frontend-setup frontend-ready seed-demo harness harness-probes match-harness docs-site docs-status taxonomy taxonomy-check

# Web frontend verification harness (the frontend analogue of `ready`).
# See frontend/harness/README.md. Runs typecheck, lint, unit, build, and the
# mocked E2E + a11y + screenshots lane; nonzero on any failure.
frontend-ready:
	cd frontend && npm run frontend-ready

# Deterministic demo world for local dev and the real-api E2E lane: designs and
# facilities curated so browse -> match -> supply tree completes. Idempotent
# (ids are content-derived), so re-running reseeds in place. `--summary` prints
# match coverage without writing.
seed-demo:
	uv run python scripts/seed_demo_data.py

# Multi-loop triage harness (parity / RED / synthetic smoke / client drift).
# Modules load independently; stubs report ok until each judge comes online.
# See harness/README.md. Not part of `make ready` (merge gate) yet.
harness:
	uv run python -m harness.runner --loops

# Production probes for Azure ACA pain points (match 503, latency, cache, OKH files).
# Enable probe modules in harness.config.json and point URLs at staging first.
harness-probes:
	uv run python -m harness.runner --probes --write-proposals

# Matching correctness (golden 3DP + MoM IRI id-alignment). Also covered by
# `make test` / `make ready`. Set MOM_LIVE=1 to include live SPARQL smoke.
# See tests/matching/ and harness/README.md.
match-harness:
	uv run pytest tests/matching -q

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

format: black ruff env-template

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

# Documentation link gate: every link into the docs must reach a real page, and
# no link may name the host that does not serve them. mkdocs validates relative
# links between pages and nothing validated the rest -- which is how the facility
# form spent months pointing at docs.openhardwaremanager.org/auth/get-a-write-key/,
# a wrong host and a page that was never written.
links-check:
	uv run python scripts/check_doc_links.py

# Regenerate the schema-owned block of .env.example from src/config/schema.py.
env-template:
	uv run python scripts/generate_env_template.py

# Staleness gate (lockfile pattern): fails if the generated block is out of date.
env-template-check:
	uv run python scripts/generate_env_template.py --check

validate-docs:
	uv run python scripts/validate_docs.py

# Process taxonomy: processes.yaml is the source of truth; the Python
# PROCESS_DEFINITIONS literal is its generated fallback (used when the YAML is
# missing or invalid). Regenerate after editing the YAML.
taxonomy:
	uv run python scripts/generate_process_definitions.py

taxonomy-check:
	uv run python scripts/generate_process_definitions.py --check

# Public docs <-> code gate. Fails when a site page claims a capability the
# code does not have (see tests/parity/test_docs_status.py). Narrative staleness
# is reported as a warning here, never as a failure.
docs-status:
	uv run pytest tests/parity/test_docs_status.py -q

# Public documentation site (openhardwaremanager.org). Stages docs-site/docs
# into docs-site/.build with status badges injected, then builds it. Authored
# markdown lives in docs-site/docs; never edit .build or site.
docs-site:
	uv run python scripts/build_docs_site.py
	uv run --extra docs mkdocs build -f docs-site/mkdocs.yml

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

# Demo-world drift gate: the client-side demo world is generated from the seed
# dataset, so the two cannot show different catalogs without CI noticing.
demo-world-check:
	uv run python scripts/generate_demo_world.py --check

# Script registry gate: fails if a script is unregistered or README is stale.
scripts-check:
	uv run python scripts/generate_scripts_index.py --check

# Service <-> API <-> CLI parity gate. Fails when a service, route, or CLI
# group drifts from the declared contract in tests/parity/manifest.py.
parity:
	uv run pytest tests/parity -q

# Confirm the API and worker container apps agree on their shared secrets.
# Deliberately NOT in `ready`: it needs live cloud credentials, and the merge
# gate must stay runnable offline. Compares digests, never values.
secrets-check:
	uv run python deploy/scripts/verify_app_secrets.py

# Definition of done. Green tests are not "ready to merge"; this is.
# Each step verifies (does not mutate) and fails fast. Run before any MR.
ready:
	@echo "==> [1/13] env verify";      $(MAKE) verify-env
	@echo "==> [2/13] format check";    $(MAKE) format-check
	@echo "==> [3/13] lint";            $(MAKE) lint
	@echo "==> [4/13] unit tests";      $(MAKE) test
	@echo "==> [5/13] service parity";  $(MAKE) parity
	@echo "==> [6/13] docs ↔ code";     $(MAKE) validate-docs
	@echo "==> [7/13] site docs status";$(MAKE) docs-status
	@echo "==> [8/13] taxonomy sync";   $(MAKE) taxonomy-check
	@echo "==> [9/13] version sync";    $(MAKE) version-check
	@echo "==> [10/13] lockfile sync";  $(MAKE) lock-check
	@echo "==> [11/13] script registry";$(MAKE) scripts-check
	@echo "==> [12/13] demo world sync";$(MAKE) demo-world-check
	@echo "==> [13/13] doc links";      $(MAKE) links-check
	@echo "==> READY: all gates passed."
