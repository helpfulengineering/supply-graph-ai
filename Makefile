# Code style and project map via uv-managed environment.
.PHONY: format format-check lint test check black ruff repo-map validate-docs parity ready

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

# Definition of done. Green tests are not "ready to merge"; this is.
# Each step verifies (does not mutate) and fails fast. Run before any MR.
ready:
	@echo "==> [1/5] format check";    $(MAKE) format-check
	@echo "==> [2/5] lint";            $(MAKE) lint
	@echo "==> [3/5] unit tests";      $(MAKE) test
	@echo "==> [4/5] service parity";  $(MAKE) parity
	@echo "==> [5/5] docs ↔ code";     $(MAKE) validate-docs
	@echo "==> READY: all gates passed."
