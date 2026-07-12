# Open Hardware Manager (OHM)

## Overview

The Open Hardware Manager (OHM) is a flexible, domain-agnostic framework designed to solve complex requirements-to-capabilities matching problems across various domains. The system matches requirements (what needs to be done) with capabilities (what can be done) to create viable solutions.

OHM exposes a FastAPI-based HTTP API that can be run locally via Docker Compose, from a [published Docker image](https://hub.docker.com/r/touchthesun/openhardwaremanager), or deployed serverlessly using the configurations in `deploy/`.

**Current release:** `0.9.0` — see [CHANGELOG.md](CHANGELOG.md) and [Release process](docs/RELEASE.md).

## Quick Start for New Users

### Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| **Git** | Clone the repository | https://git-scm.com/downloads |
| **Docker Desktop** | Run the API server | https://www.docker.com/products/docker-desktop/ |
| **uv** | Python env + CLI (local dev) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` or `brew install uv` |
| **Node.js ≥ 18** | Reference frontend | https://nodejs.org/ |

> Docker Desktop is sufficient if you only want to run the API. Install `uv` when you need the `ohm` CLI, to run tests, or to work on Python code.

After installing, open a new terminal so the tools are on your PATH.

### Option A: Published Docker image (fastest — no clone required)

**Local storage (no credentials needed):**

```bash
docker pull touchthesun/openhardwaremanager:0.9.0
docker run -p 8001:8001 \
  -e STORAGE_PROVIDER=local \
  -e LLM_ENABLED=false \
  touchthesun/openhardwaremanager:0.9.0
```

**Remote storage (Azure Blob, AWS S3, or GCS):**

The published image does not include a `.env` file — you must pass your storage credentials at runtime. The simplest way is `--env-file`:

```bash
# Copy the template, fill in your provider and credentials, then:
docker run -p 8001:8001 \
  --env-file .env \
  touchthesun/openhardwaremanager:0.9.0
```

The minimum `.env` keys for Azure Blob are:

```
STORAGE_PROVIDER=azure_blob
AZURE_STORAGE_ACCOUNT=<your-account-name>
AZURE_STORAGE_KEY=<your-account-key>
AZURE_STORAGE_CONTAINER=<your-container-name>
```

See [Container Guide](docs/development/container-guide.md) for the full list of storage env vars and examples for AWS S3 and GCS.

> **How configuration resolves.** Non-secret defaults (storage provider / account
> / container, `OKW_SOURCE`, CORS) are checked in per environment under
> `config/environments/<ENVIRONMENT>.toml` and selected by `ENVIRONMENT`; anything
> you pass as an env var (or in `.env`) overrides them. Secrets — `AZURE_STORAGE_KEY`,
> `API_KEYS`, `LLM_*` — are never in those files (use `.env` or an Azure `secretRef`).
> In `production` the app hard-fails on missing/invalid storage config, and `/health`
> reports the resolved storage target + object counts. See the
> [Developer Guide](docs/development/developer-guide.md) for details.

The API is at `http://localhost:8001`. Docs: `http://localhost:8001/v1/docs`. Check version: `curl -s http://localhost:8001/health`.

Images support **linux/amd64** and **linux/arm64** (Apple Silicon and x86-64). Federation is **disabled by default**. Enable with `-e OHM_FEDERATION_ENABLED=true` only when you intend to run peer sync (see [federation docs](docs/development/federation-infra.md)).

### Option B: API server from source (Docker Compose)

```bash
# 1. Clone
git clone https://github.com/helpfulengineering/supply-graph-ai.git
cd supply-graph-ai

# 2. Create your environment file (defaults work for local development)
cp env.template .env

# 3. Build and start the API
docker compose up ohm-api
```

The API is now available at `http://localhost:8001`. Interactive API docs are at `http://localhost:8001/v1/docs`.

### Option C: Local development with uv (CLI + tests + scripts)

`uv` manages both the Python version and the virtual environment — no separate Python installation or conda is needed.

```bash
# 1. Clone
git clone https://github.com/helpfulengineering/supply-graph-ai.git
cd supply-graph-ai

# 2. Create your environment file
cp env.template .env

# 3. Provision the environment (one step)
make setup

# 4. Activate the virtual environment
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# 5. Verify the CLI is available
ohm --help

# 6. Start the API server
docker compose up -d ohm-api
```

`make setup` creates `.venv`, installs **all** dependencies (runtime + dev tools
for tests, so `uv run pytest` uses this venv rather than a foreign interpreter on
`PATH`), **including the spaCy NLP model** `en_core_web_md` — which is pinned in
`uv.lock`, so you never install it by hand. It then verifies the environment is
fully online, and is safe to re-run any time to repair or refresh it.

You can also run one-off commands without activating the venv:

```bash
uv run ohm system health
uv run pytest tests -m unit
```

### Helpful Docker commands

```bash
# Start in the background
docker compose up -d ohm-api

# Tail logs
docker compose logs -f ohm-api

# Rebuild after Python source changes
docker compose up --build ohm-api

# Stop everything
docker compose down
```

### Reference demo frontend (optional)

The repository includes a Vite + React reference UI under `frontend/`. It provides a browser-based interface for browsing OKH designs, running matches, and visualising supply-chain solutions.

**Step 1 — start the API** (must be running before the frontend is useful):

```bash
docker compose up -d ohm-api
```

**Step 2 — start the frontend dev server** (requires Node.js ≥ 18):

```bash
cd frontend
npm install   # first time only — installs JS dependencies
npm run dev
```

Open the URL Vite prints (typically `http://localhost:5173`).

The dev server proxies all `/v1` requests to the OHM API. If your API is not at the default `http://localhost:8001`, copy `frontend/.env.example` to `frontend/.env` and set `OHM_API_BASE_URL` accordingly.

> **Hot-reload:** The frontend picks up TypeScript/CSS changes automatically while `npm run dev` is running. Python backend changes require rebuilding and restarting the Docker container (`docker compose up --build ohm-api`).

## Documentation

This README provides a quick start guide and basic project information. For full documentation, run MkDocs locally.

### Building Documentation Locally

The OHM documentation is built using [MkDocs](https://www.mkdocs.org/).

```bash
# Install docs dependencies (MkDocs + plugins) into the project venv
uv sync --extra docs

# Serve with live reload
uv run mkdocs serve
```

Open your browser to `http://localhost:8000/`.

> Port 8000 is the MkDocs server. The API server runs on port 8001.

### Documentation Structure

Our documentation covers:

- **Architecture Guide**: System design, components, and data flow
  - System architecture overview
  - Data flow diagrams
  - Component interactions
  - Validation and matching pipelines

- **Domain Implementations**:
  - Manufacturing domain (OKH/OKW matching)
  - Cooking domain (Recipe/Kitchen matching)
  - Domain extension guidelines

- **API Reference**:
  - RESTful API endpoints
  - Authentication
  - Request/Response formats
  - Usage examples

- **Developer Guide**:
  - Setup and installation
  - Contributing guidelines
  - Testing procedures
  - Best practices


## Project Structure

```markdown
supply-graph-ai/
├── docs/                   # Documentation files (MkDocs)
├── deploy/                 # Cloud agnostic deployment
├── scripts/                # Utility scripts for dev & testing
├── src/                    # Source code
│   ├── core/               # Core framework components
│   │   ├── api/            # API endpoints
│   │   ├── domains/        # Domain implementations
│   │   ├── errors/         # Centralized error handling
│   │   ├── generation/     # Create OKH from external project
│   │   ├── llm/            # LLM service and provider abstraction layer
│   │   ├── matching/       # Matching Rules Manager
│   │   ├── models/         # Data models
│   │   ├── packaging/      # Service for building and storing OKH Packages
│   │   ├── registry/       # Domain registry
│   │   ├── services/       # Core services
│   │   ├── storage/        # Storage service for remote file mgmt
│   │   ├── utils/          # Utility functions
│   │   └── validation/     # Validation Engine
│   ├── cli/                # Command Line Interface
│   └── config/             # Config management
├── synth/                  # synthetic data for development, remove in prod
├── tests/                  # Test files for development
├── mkdocs.yml              # Documentation configuration
├── bin/                    # Development entrypoint scripts
│   └── ohm                 # Development CLI entrypoint (fallback)
├── pyproject.toml          # Package metadata and dependencies
├── uv.lock                 # Locked dependency versions (managed by uv)
└── docker-compose.yml      # Local service orchestration
```

## Running the Application

### API server (Docker)

```bash
# Start (or rebuild) the API server
docker compose up --build ohm-api

# API base URL:      http://localhost:8001
# Interactive docs:  http://localhost:8001/v1/docs
```

### CLI commands (requires uv setup from Option C above)

```bash
# Health check
ohm system health

# Or without activating the venv
uv run ohm system health
```

For container deployment guides, see the [Container Guide](docs/development/container-guide.md) in our documentation.
