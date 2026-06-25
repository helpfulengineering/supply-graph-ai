# Code style and project map via uv-managed environment.
.PHONY: format format-check lint test check black ruff repo-map validate-docs parity e2e ready

format: black ruff repo-map

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

validate-docs:
	uv run python scripts/validate_docs.py

# Service <-> API <-> CLI parity gate. Fails when a service, route, or CLI
# group drifts from the declared contract in tests/parity/manifest.py.
parity:
	uv run pytest tests/parity -q

# Placeholder. Intentionally fails until wired up so `make ready` cannot go
# green on an unrun end-to-end suite. Replace the body with the real run, e.g.:
#   docker compose -f docker-compose.federation.yml up --build -d
#   ./scripts/federation_e2e.sh
e2e:
	@echo "make e2e: NOT WIRED UP — implement the live-API E2E run here." >&2
	@echo "  See scripts/federation_e2e.sh for an existing smoke test to build on." >&2
	@exit 1

# Definition of done. Green tests are not "ready to merge"; this is.
# Each step verifies (does not mutate) and fails fast. Run before any MR.
ready:
	@echo "==> [1/6] format check";    $(MAKE) format-check
	@echo "==> [2/6] lint";            $(MAKE) lint
	@echo "==> [3/6] unit tests";      $(MAKE) test
	@echo "==> [4/6] service parity";  $(MAKE) parity
	@echo "==> [5/6] docs ↔ code";     $(MAKE) validate-docs
	@echo "==> [6/6] live E2E";        $(MAKE) e2e
	@echo "==> READY: all gates passed."
