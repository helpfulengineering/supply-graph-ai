### Development environment (uv)

- Install [**uv**](https://docs.astral.sh/uv/) and, from the repository root, run **`uv sync --extra dev`** so Python 3.12, dependencies from **`pyproject.toml` / `uv.lock`**, and **`pytest`** live in **`.venv`**.
- Run tools and tests with **`uv run …`** (for example `uv run pytest`, `uv run ohm --help`) so you do not accidentally use a global interpreter whose packages drift from the lockfile.
- Optional: **`uv sync --extra docs`** for MkDocs; **`uv sync --all-extras`** if you need every optional group.

### Testing Guidelines

- Unit tests required for all new features
- Integration tests for API endpoints
- End-to-end tests for complete workflows
- Use pytest fixtures for common test setups
- Mock external services appropriately

### Pull Request Process

1. Create feature branch
2. Write tests
3. Implement features
4. Run test suite
5. Submit PR with description
6. Address review comments

### Documentation

- Update relevant documentation with code changes
- Include docstrings for public interfaces
- Maintain example usage in docs
- Update API documentation when endpoints change