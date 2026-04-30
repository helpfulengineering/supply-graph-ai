# Code style and project map via uv-managed environment.
.PHONY: format format-check lint test check black ruff repo-map

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
