# Code style and project map (activate your Python env first, e.g. conda activate supply-graph-ai).
.PHONY: format black ruff repo-map

format: black ruff repo-map

black:
	black .

ruff:
	ruff check src --fix

repo-map:
	python scripts/generate_repo_map.py
