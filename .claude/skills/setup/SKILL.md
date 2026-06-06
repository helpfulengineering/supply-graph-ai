---
name: setup
description: Set up and configure Open Hardware Manager (OHM). Use when the user says "set up", "configure", "install", "get started", asks about environment variables, configuration, or wants help troubleshooting installation. Also use when the user has a question answered by the project documentation.
version: 1.0.0
metadata:
  generated_by: scaffold-setup-skill
  generated_at: 2026-06-04
---

# Open Hardware Manager (OHM) Setup

Natural language setup wizard for OHM. Covers environment detection, configuration, dependency installation, infrastructure, developer onboarding, and documentation Q&A.

**Project summary:** OHM is a flexible, domain-agnostic framework that matches requirements (OKH hardware designs) with capabilities (OKW manufacturing facilities) across domains like manufacturing and cooking.

## Arguments

`$ARGUMENTS` may contain:
- `--dry-run` — walk through the full setup flow without making any changes
- `--section <name>` — jump to a specific section: `detect`, `config`, `deps`, `infra`, `workflow`, `docs`, `health`
- `--regenerate-docs-index` — rebuild the documentation index from current MkDocs content

---

## Step 1: Environment Detection

Before asking any questions, check what is already in place. Report a status table (done / missing / error).

**Existing configuration:**
- Check for `.env` file in the repo root — if present, read it and note which params are set; list missing required params
- Check for `frontend/.env` (only relevant if user wants the frontend)

**Runtime prerequisites:**
- Python: `python3 --version` (need ≥ 3.12) OR check for `uv`: `uv --version`
- Docker: `docker info` (must be running) — required for Options A and B
- Node.js: `node --version` (need ≥ 18) — only if user wants the frontend dev server
- `uv`: `uv --version` — required for Option C (local Python dev)

**Infrastructure:**
- Docker running: `docker info`
- If `.env` exists and `STORAGE_PROVIDER=aws_s3/azure_blob/gcp_storage`: confirm cloud credentials are set

After detection: summarize what's done vs. what still needs setup. If `.env` is fully configured and Docker is running, offer to go straight to the health check (Step 7).

If `--dry-run` is active, note this at the top: "Dry run mode — no changes will be made."

---

## Step 2: Setup Path Selection

Ask which setup path the user wants:

"How do you want to run OHM?"
- **Option A — Published Docker image**: Fastest. No clone required. Use when you just want to run the API, not develop it. Requires Docker Desktop.
- **Option B — Docker Compose from source**: Recommended for most users. Clone → configure → `docker compose up`. Requires Docker Desktop.
- **Option C — Local Python development (uv)**: Required for CLI development, running tests, or modifying Python code. Requires `uv`.

Save the answer as `$SETUP_PATH` and use it to gate questions in Steps 3 and 4.

---

## Step 3: Configuration

Collect values for all required (and relevant optional) parameters. Skip any param already present in `.env`.

### 3a: Environment

Ask: "Are you setting this up for local development or production?"
- `development` — defaults are safe; encryption keys are optional; CORS is open
- `production` — encryption keys required; CORS must be restricted; API keys must be set

Save as `$ENV_MODE`. Questions marked `[prod only]` are skipped for dev.

### 3b: API Authentication

Always ask — even in development, this prevents accidental open access.

**`API_KEYS`** — Comma-separated list of API keys (backward-compatible; storage-based auth is available separately)
- Ask: "Do you have an API key, or should I generate one?"
  - Generate: run `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` and use it
  - Provide: paste it in
- Note: treat as secret — do not echo back to user
- is_secret: true

**`AUTH_MODE`** — default: `hybrid` (accepts both env-var keys and storage-based keys)
- Optional — only ask if user wants to change: enum: `env`, `storage`, `hybrid`
- For most users, leave as `hybrid`

### 3c: Storage Provider

**`STORAGE_PROVIDER`** — Where OHM stores OKH/OKW data files
- Ask: "Which storage backend are you using?"
  - `local` (default, recommended for getting started) → ask for `LOCAL_STORAGE_PATH`
  - `aws_s3` → branch to AWS params
  - `azure_blob` → branch to Azure params
  - `gcp_storage` → branch to GCP params

**If `local`:**
- **`LOCAL_STORAGE_PATH`** — default: `./storage`; ask only if user wants a custom path
- `STORAGE_BUCKET_NAME` — default: `ohm-storage`; skip for most users

**If `aws_s3`:**
- **`AWS_ACCESS_KEY_ID`** — required; type: secret; is_secret: true
- **`AWS_SECRET_ACCESS_KEY`** — required; type: secret; is_secret: true
- **`AWS_DEFAULT_REGION`** — default: `us-east-1`; ask if different
- **`AWS_S3_BUCKET`** — required; bucket name

**If `azure_blob`:**
- **`AZURE_STORAGE_ACCOUNT`** — required (canonical name used in code)
- **`AZURE_STORAGE_KEY`** — required; type: secret; is_secret: true
- **`AZURE_STORAGE_CONTAINER`** — required
- Note: `AZURE_STORAGE_ACCOUNT_NAME`, `AZURE_STORAGE_ACCOUNT_KEY`, `AZURE_CONTAINER_NAME` are legacy aliases — set both canonical and legacy if the user's workflow requires the legacy names
- Optional: `AZURE_STORAGE_OKH_CONTAINER_NAME` (default: `okh`), `AZURE_STORAGE_OKW_CONTAINER_NAME` (default: `okw`)
- Optional: `AZURE_STORAGE_SERVICE_NAME` — storage service URL for OKH/OKW libraries; leave empty unless required by your Azure setup

**If `gcp_storage`:**
- **`GCP_PROJECT_ID`** — required
- **`GCP_STORAGE_BUCKET`** — required
- **`GCP_CREDENTIALS_JSON`** — required; service account JSON; type: secret; is_secret: true
- `GOOGLE_CLOUD_PROJECT_ID` — legacy alias for `GCP_PROJECT_ID`; set both for backward compatibility
- `GOOGLE_CLOUD_STORAGE_BUCKET` — legacy alias for `GCP_STORAGE_BUCKET`; set both for backward compatibility

### 3d: LLM Integration

**`LLM_ENABLED`** — default: `false`
- Ask: "Do you want to enable LLM integration (AI-powered OKH manifest generation and enhanced matching)?"
  - No → set `LLM_ENABLED=false`, skip all LLM params
  - Yes → branch to LLM params below

**If LLM enabled:**

**`LLM_DEFAULT_PROVIDER`** / **`LLM_PROVIDER`** — which LLM provider to use
- Ask: "Which LLM provider?"
  - `anthropic` (default) → requires `ANTHROPIC_API_KEY`
  - `openai` → requires `OPENAI_API_KEY`; optionally `OPENAI_ORGANIZATION_ID`
  - `google` → requires `GOOGLE_AI_API_KEY`
  - `azure` → requires `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`; default version: `2024-02-15-preview`
  - `local` (Ollama) → requires `OLLAMA_BASE_URL` (default: `http://localhost:11434`)

Provider-specific secrets (ask immediately after provider selection):
- **`ANTHROPIC_API_KEY`** — is_secret: true
- **`OPENAI_API_KEY`** — is_secret: true
- **`GOOGLE_AI_API_KEY`** — is_secret: true
- **`AZURE_OPENAI_API_KEY`** — is_secret: true
- **`AZURE_OPENAI_ENDPOINT`** — url; format: `https://<resource>.openai.azure.com/`
- `AZURE_OPENAI_API_VERSION` — default: `2024-02-15-preview`; leave as default unless your Azure deployment uses a different version

**`LLM_DEFAULT_MODEL`** / **`LLM_MODEL`** — default: `claude-3-sonnet-20240229` (for anthropic); leave as default for most users

**`LLM_QUALITY_LEVEL`** — enum: `hobby`, `professional`, `medical`; default: `professional`

**`LLM_STRICT_MODE`** — boolean; default: `false`; enables stricter LLM validation

**LLM Encryption** (required in production if LLM enabled):
- Ask: "Are you setting this up for production?"
  - Dev: warn that defaults are used (not secure for production), skip encryption params
  - Prod: encryption credentials are **required**:
    - **`LLM_ENCRYPTION_SALT`** — required for prod; is_secret: true; warn: must not be a default value
    - **`LLM_ENCRYPTION_PASSWORD`** — required for prod; is_secret: true; warn: must not be a default value
    - Alternatively, **`LLM_ENCRYPTION_KEY`** — a pre-generated Fernet key (32 url-safe base64 bytes); leave empty if using salt/password approach
    - Note: do not add inline comments on the same line as an empty `LLM_ENCRYPTION_KEY=` value — python-dotenv will treat the comment as the value

### 3e: Optional Features

Present as a menu — user can skip all:

"Here are optional features you can configure. Which, if any, would you like to enable?"

**Federation** (multi-node OHM network):
- **`OHM_FEDERATION_ENABLED`** — default: false; enable only if you intend to run peer sync
- If enabled:
  - `OHM_FEDERATION_NODE_NAME` — human-readable name; default: "My OHM Node"
  - `OHM_FEDERATION_NODE_ROLE` — default: `peer`
  - `OHM_FEDERATION_DATA_DIR` — default: `/app/storage/federation`
  - `OHM_FEDERATION_MANUAL_PEERS` — optional; comma-separated peer URLs
  - `OHM_FEDERATION_MDNS_ENABLED` — boolean; optional (auto-discovery)
  - `OHM_FEDERATION_SYNC_INTERVAL_SEC` — integer; default: 60
  - `OHM_FEDERATION_SYNC_RATE_LIMIT_PER_MIN` — integer; optional; default: 60
  - Note: federation vars must be set in container env (via docker-compose), not just exported in the host shell
  - Suggest: copy `.env.federation.example` values into `.env`

**Advanced API settings** (rarely needed):
- `CORS_ORIGINS` — default: `*` (dev), empty (prod); ask only in prod if user needs to restrict
- `API_HOST` — default: `0.0.0.0`; only change if binding to a specific interface
- `API_PORT` — default: `8001`; only change if the port conflicts
- `AUTH_ENABLE_STORAGE` — boolean; default: `true`; enable storage-based API key management
- `AUTH_CACHE_TTL` — integer seconds; default: `300`; cache TTL for validated keys
- `AUTH_KEY_LENGTH` — integer; default: `32`; length in bytes for generated API keys
- `LOG_FILE` — path; default: `logs/app.log`
- `OHM_SERVER_URL` — url; default: `http://localhost:8001`; CLI default server URL (set this if your API is on a different port or host)

**Cache settings** (rarely needed):
- `CACHE_ENABLED` — boolean; default: `true`
- `CACHE_MAX_SIZE` — integer; default: `1000`; max LRU cache entries
- `CACHE_CLEANUP_INTERVAL` — integer seconds; default: `60`

**Rate limiting** (rarely needed):
- `RATE_LIMIT_ENABLED` — boolean; default: `true`
- `RATE_LIMIT_CLEANUP_INTERVAL` — integer seconds; default: `60`

**Matching tuning:**
- `MAX_DEPTH` — BOM explosion depth; default: 5; range 1–10; only ask if user has performance concerns

**Domain toggles:**
- `COOKING_DOMAIN_ENABLED` — default: true
- `MANUFACTURING_DOMAIN_ENABLED` — default: true

**Developer/testing:**
- `DEV_MODE` — default: false
- `LOG_LEVEL` — default: INFO; enum: DEBUG/INFO/WARNING/ERROR
- `TEST_DATA_DIR` — default: test-data

**Repository URLs** (optional, for documentation/examples only):
- `OKH_LIBRARY_REPO_URL` — url; optional; repository URL for the OKH library
- `OKF_SCHEMA_REPO_URL` — url; optional; repository URL for the OKF schema

---

## Step 4: Config File Generation

Write collected answers to `.env` in the repo root.

Format:
```
# Generated by OHM setup skill on <date>
# Edit this file to change configuration. See env.template for all options.

ENVIRONMENT=<value>
API_KEYS=<value>
STORAGE_PROVIDER=<value>
# ... only params relevant to chosen options
```

Rules:
- Only write params relevant to the chosen storage provider and enabled features
- Do not write cloud provider params for providers that are not selected
- Write secret params without quoting and without inline comments (especially for empty LLM_ENCRYPTION_KEY)
- Never overwrite params already present in `.env` unless user explicitly confirmed replacement
- Add a comment block before each logical section (storage, LLM, federation)

For **Option A** (published Docker image), instead of writing a `.env` file, show the equivalent `docker run` command with `-e` flags or `--env-file` usage.

If `--dry-run` is active: show the would-be `.env` contents but do not write the file.

---

## Step 5: Dependency Installation

Run in order. Stop and report if any step fails.

### Option A: Published Docker image

```bash
docker pull touchthesun/openhardwaremanager:latest
```

Then run with `--env-file .env` or explicit `-e` flags:
```bash
docker run -p 8001:8001 --env-file .env touchthesun/openhardwaremanager:latest
```

Or for local storage with no credentials:
```bash
docker run -p 8001:8001 \
  -e STORAGE_PROVIDER=local \
  -e LLM_ENABLED=false \
  touchthesun/openhardwaremanager:latest
```

### Option B: Docker Compose from source

No Python install needed — Docker builds the image.

```bash
# 1. Create .env from template (if not already done in Step 4)
cp env.template .env

# 2. Build and start
docker compose up --build ohm-api
```

To include Prometheus monitoring:
```bash
docker compose --profile monitoring up
```

### Option C: uv local development

Prerequisite: `uv` must be installed (`curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`)

```bash
# Install all dependencies (creates .venv automatically)
uv sync

# For development dependencies (pytest, etc.)
uv sync --extra dev

# Activate the virtual environment
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# Verify the CLI is available
ohm --help
```

---

## Step 6: Infrastructure Setup

### Start the API server

**Option B (Docker Compose):**
```bash
# Foreground (shows logs):
docker compose up ohm-api

# Background:
docker compose up -d ohm-api

# Tail logs:
docker compose logs -f ohm-api

# Rebuild after Python source changes:
docker compose up --build ohm-api

# Stop:
docker compose down
```

**Option C (local Python):**
```bash
# Start the API directly with uvicorn (dev mode)
uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8001 --reload

# Or via the Docker container (most common even for local dev)
docker compose up -d ohm-api
```

### Storage initialization

For **local storage**: no action needed — OHM creates the directory structure on first use.

For **cloud storage**: verify credentials by making a test API call after the server starts:
```bash
curl -s http://localhost:8001/health
```

---

## Step 7: Developer Workflow Onboarding

Brief the user on day-to-day development commands.

### Running the API
```bash
# Option B/C: start via Docker Compose
docker compose up -d ohm-api
# Access at: http://localhost:8001
# Interactive API docs: http://localhost:8001/v1/docs
# Health check: curl http://localhost:8001/health
```

### Using the CLI (Option C only)
```bash
# System health
ohm system health

# OKH operations
ohm okh list-manifests
ohm okh upload path/to/manifest.yaml
ohm okh validate <id>

# OKW operations
ohm okw list-files
ohm okw search --query "CNC machining"

# Matching
ohm match --okh <okh-id> --domain manufacturing

# LLM (if enabled)
ohm llm providers info
ohm okh generate-from-url https://github.com/example/hardware-project
```

### Running tests
```bash
# Unit tests (fast, no external services)
uv run pytest tests -m unit

# All non-quarantined tests
uv run pytest

# With coverage
uv run pytest --cov=src tests -m unit
```

### Code quality
```bash
make lint          # ruff + bandit
make format        # black + ruff
make format-check  # verify formatting (no changes)
make check         # lint + format-check + test
```

### Common Docker commands
```bash
docker compose up -d ohm-api          # start in background
docker compose logs -f ohm-api        # tail logs
docker compose up --build ohm-api     # rebuild after source changes
docker compose down                   # stop all services
docker compose --profile monitoring up # start with Prometheus
```

### Environment files
- `env.template` — canonical template with all params documented; copy to `.env`
- `.env.federation.example` — federation vars; copy into `.env` to enable federation
- `config/llm_config.json.example` — advanced LLM provider config; copy to `config/llm_config.json` for fine-grained control (optional; env vars take precedence for most use cases)

---

## Core Workflows: Matching and generate-from-url

These are the two highest-value features in OHM. Walk users through these after the API is running and data is loaded.

---

### Workflow 1: Generate an OKH manifest from a GitHub URL

`generate-from-url` uses LLM to analyze a hardware project repo and produce a structured OKH manifest. **Requires LLM to be enabled** (see Step 3d).

**What it does:** Fetches the repository, reads README/docs/source, and generates a structured OKH manifest describing the hardware's requirements, processes, and materials.

**Via CLI (Option C):**
```bash
# Basic — uses default LLM provider from .env
ohm okh generate-from-url https://github.com/<owner>/<repo> --use-llm

# Specify provider and model explicitly
ohm okh generate-from-url https://github.com/<owner>/<repo> \
  --llm-provider anthropic \
  --llm-model claude-sonnet-4-5-20250929

# Save manifest to a file
ohm okh generate-from-url https://github.com/<owner>/<repo> \
  --use-llm \
  --output my_manifest.okh.json
```

**Via REST API:**
```bash
curl -X POST http://localhost:8001/v1/api/okh/generate-from-url \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d '{"url": "https://github.com/<owner>/<repo>"}'
```

**What to expect:**
- The call may take 10–60 seconds depending on repo size and LLM provider latency
- The response is a full OKH manifest JSON; the manifest is also stored in OHM's storage
- If LLM is disabled, a stub manifest is generated from metadata only (no deep analysis)

**If the call fails:**
- Check `LLM_ENABLED=true` and the relevant API key are set in `.env`
- Check LLM health: `ohm llm providers info` or `curl http://localhost:8001/v1/api/llm/health`
- Check server logs: `docker compose logs -f ohm-api`

---

### Workflow 2: Match an OKH manifest to OKW facilities

Matching connects a hardware design (OKH) to manufacturing facilities (OKW) that can produce it. **Requires at least one OKH manifest and at least one OKW facility to be loaded into storage.**

#### Step A: Load data

**Option 1 — Use test data bundled in the repo:**
```bash
# Upload an OKH manifest from the test-data directory
ohm okh upload test-data/okh/example-manifest.json

# Upload an OKW facility
ohm okw upload test-data/okw/example-facility.json
```

**Option 2 — Generate an OKH manifest from a URL (Workflow 1 above), then upload a facility file you have:**
```bash
ohm okw upload /path/to/your/facility.json
```

**Verify data is loaded:**
```bash
ohm okh list-manifests    # should show at least one entry
ohm okw list-files        # should show at least one facility
```

#### Step B: Run a match

```bash
# Basic match — OHM auto-detects the domain
ohm match requirements <path-to-okh-manifest.json>

# Explicit manufacturing domain
ohm match requirements manifest.json --domain manufacturing

# Enhanced match with LLM analysis (higher quality, slower)
ohm match requirements manifest.json \
  --use-llm \
  --llm-provider anthropic \
  --quality-level professional

# Match against a specific facility by ID
ohm match requirements manifest.json \
  --facility-id <facility-uuid>

# Filter by location and minimum confidence
ohm match requirements manifest.json \
  --location "San Francisco" \
  --min-confidence 0.8
```

**Via REST API:**
```bash
curl -X POST http://localhost:8001/v1/api/match \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your-api-key>" \
  -d @manifest.json
```

**What to expect:**
- The response includes matched facilities with confidence scores
- Each match entry shows which requirements were satisfied and which were gaps
- Higher `--quality-level` values produce more thorough validation but require more LLM tokens

**If no matches are returned:**
- Confirm OKW facilities are loaded: `ohm okw list-files`
- Try without `--domain` to let OHM auto-detect
- Lower `--min-confidence` if you have a threshold set
- Check domain health: `ohm utility domains`

#### Step C: Save and inspect solutions

```bash
# List recent matches
ohm match list-recent --limit 10

# Save a match result as a supply-tree solution
ohm solution save match-output.json --ttl-days 30

# List saved solutions
ohm solution list
```

---

## Step 8: Health Check

Verify the setup is working.

1. **API health:**
   ```bash
   curl -s http://localhost:8001/health
   ```
   Expected: `{"status": "healthy", ...}`

2. **API docs accessible:**
   Open `http://localhost:8001/v1/docs` in a browser — should show the Swagger UI.

3. **Storage check** (via CLI, Option C):
   ```bash
   ohm system health
   ```

4. **LLM check** (if LLM enabled):
   ```bash
   curl -s http://localhost:8001/v1/api/llm/health
   # Or via CLI:
   ohm llm providers info
   ```

5. **Run unit tests** (Option C):
   ```bash
   uv run pytest tests -m unit
   ```

Report: "Setup complete. OHM is running at http://localhost:8001." — or list any errors.

---

## Documentation Q&A

When the user asks a question about OHM configuration, features, or usage, find the answer using this index.

**Documentation index** — generated 2026-06-04

| Section | File | Summary |
|---------|------|---------|
| Home / Overview | docs/index.md | Documentation contents and navigation map |
| Project Overview | docs/overview.md | Core problem space: matching OKH hardware designs with OKW manufacturing facilities |
| Cheatsheet | docs/cheatsheet.md | Quick reference for all major capabilities, API endpoints, and CLI commands |
| Architecture Overview | docs/architecture/index.md | Core components: domain management, matching layers, storage, generation |
| Matching Architecture | docs/architecture/matching.md | How the multi-layer matching system connects requirements to capabilities |
| Storage Architecture | docs/architecture/storage.md | Storage abstraction layer; local, S3, Azure, GCS provider details |
| Generation Architecture | docs/architecture/generation.md | 4-layer progressive OKH manifest enhancement system |
| Services Architecture | docs/architecture/services.md | Service layer design and inter-component communication |
| Process Taxonomy ADR | docs/architecture/process-taxonomy-adr.md | Architectural decision record for process taxonomy |
| System Diagram | docs/architecture/system-diagram.md | High-level system architecture diagram |
| Data Flow Diagram | docs/architecture/data-flow-diagram.md | How data moves through the OHM pipeline |
| Workflow Generation | docs/architecture/workflow-generation.md | Workflow generation architecture |
| API Overview | docs/api/index.md | FastAPI-based REST API; use /v1/docs on a running server for live reference |
| API Authentication | docs/api/auth.md | API key auth, storage-based keys, AUTH_MODE configuration |
| API Routes & Models | docs/api/routes.md | All REST endpoints for OKH, OKW, matching, supply trees, and LLM operations |
| LLM Overview | docs/llm/index.md | Multi-provider LLM integration: Anthropic, OpenAI, Azure, Google, local (Ollama) |
| LLM Configuration | docs/llm/configuration.md | Environment variables and llm_config.json for LLM setup |
| LLM API Reference | docs/llm/api.md | LLM REST endpoints and request/response schemas |
| LLM CLI Commands | docs/llm/cli.md | ohm llm subcommands: generate, generate-okh, providers info |
| LLM Generation Layer | docs/llm/generation.md | How LLM enhances OKH manifest generation |
| LLM Examples | docs/llm/examples.md | Practical LLM usage examples |
| LLM Service | docs/llm/llm-service.md | LLM service internals and provider abstraction |
| LLM Quick Start | docs/llm/llm-quick-start.md | Fastest path to enabling LLM features |
| CLI Overview | docs/CLI/index.md | Complete CLI reference; two modes: HTTP API and direct service fallback |
| CLI Quick Start | docs/CLI/quick-start.md | Get up and running with the ohm CLI in 5 minutes |
| CLI Examples | docs/CLI/examples.md | Practical workflows for common CLI use cases |
| CLI Architecture | docs/CLI/architecture.md | CLI implementation design and extension points |
| Matching Overview | docs/matching/index.md | Multi-layer matching system: direct → heuristic → NLP |
| Direct Matching | docs/matching/direct-matching.md | Exact-match algorithm for requirements ↔ capabilities |
| Heuristic Matching | docs/matching/heuristic-matching.md | Heuristic scoring and fuzzy matching strategies |
| NLP Matching | docs/matching/nlp-matching.md | Natural language understanding for semantic matching |
| Developer Guide | docs/development/developer-guide.md | How to set up a local dev environment and contribute |
| Container Guide | docs/development/container-guide.md | Docker and docker-compose workflows; all storage env vars |
| Roadmap | docs/development/roadmap.md | Planned features and development priorities |
| Conference Demo Readiness | docs/development/conference-demo-readiness.md | Demo setup checklist; how to regenerate OpenAPI route counts |
| Data Models Overview | docs/models/index.md | Supply trees, BOM, process requirements, and validation contexts |
| Bill of Materials | docs/models/bom.md | BOM data model for nested component requirements |
| Supply Trees | docs/models/supply-tree.md | Central data structure for manufacturing solutions |
| Process Requirements | docs/models/process.md | Process requirement and capability modeling |
| Validation Contexts | docs/models/validation.md | Domain-aware validation with quality levels (hobby/professional/medical) |
| OKH Documentation | docs/models/okh-docs.md | OpenKnowHow manifest format reference |
| OKW Documentation | docs/models/okw-docs.md | OpenKnowWhere facility format reference |
| OKW Specification | docs/models/okw-specification.md | Full OKW specification |
| Format Conversion | docs/conversion/index.md | Bi-directional OKH ↔ external format conversion (MSF Datasheet) |
| MSF Datasheet | docs/conversion/msf-datasheet.md | Convert between OKH and MSF .docx datasheet format |
| Matching Accuracy Baseline | docs/metrics/matching-accuracy-baseline.md | Baseline metrics for matching algorithm accuracy |
| Domains Overview | docs/domains/index.md | Multi-domain system: manufacturing and cooking; domain detection and health |
| Manufacturing Domain | docs/domains/manufacturing.md | Manufacturing-specific extractors, matchers, and validators |
| Cooking Domain | docs/domains/cooking.md | Cooking domain components and use cases |

**To answer a documentation question:**
1. Find the most relevant file(s) from the index above
2. Read that file
3. Answer from its content, citing the section

**To regenerate this index** after documentation changes:
Run this skill with `--regenerate-docs-index`.

---

## Anti-patterns

- Don't set params the user hasn't provided
- Don't skip the health check — a broken setup is worse than a slow one
- Don't store secret values in conversation history; handle them write-only
- If a step fails, stop and report the error — don't continue to the next step
- Don't set LLM_ENCRYPTION_KEY with an inline comment on the same line when the value is empty — python-dotenv will treat the comment as the value
- Don't enable federation unless the user explicitly wants multi-node peer sync; it adds complexity with no benefit for single-node setups
- For cloud storage, don't write both canonical and legacy Azure env var names unless the user's toolchain requires the legacy names
