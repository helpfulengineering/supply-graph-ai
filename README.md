# Open Hardware Manager (OHM)

## Overview

The Open Hardware Manager (OHM) is a flexible, domain-agnostic framework designed to solve complex requirements-to-capabilities matching problems across various domains. The system matches requirements (what needs to be done) with capabilities (what can be done) to create viable solutions.


## Quick Start for Developers

### Quick Start Script (Recommended)

The easiest way to get started is using the automated bring-up script. This handles environment configuration, container orchestration, and optional LLM setup in one command.

```bash
# Basic setup (starts API and core services)
./scripts/bringup.sh

# Setup with local LLM support (automatically handles Ollama)
./scripts/bringup.sh --with-llm

# Setup with specific LLM model
./scripts/bringup.sh --with-llm --model mistral

# Reset environment (clean start)
./scripts/bringup.sh --reset
```

**Key Options:**
- `--with-llm`: Enables LLM support. Uses existing local Ollama if detected, or starts a containerized instance.
- `--model <name>`: Specifies the Ollama model to use (default: `llama3.1:8b`).
- `--clean`: Stops containers and removes volumes (`docker-compose down -v`).
- `--reset`: Deep cleans the repository (removes build artifacts, `.env`, etc) and restarts.
- `--help`: Shows all available options.

### Installation

#### Option 1: Docker Compose (Manual)

Docker Compose is the recommended way to run the OHM server. It handles all dependencies, configuration, and provides a consistent environment.

```bash
# Clone the repository
git clone https://github.com/helpfulengineering/supply-graph-ai.git
cd supply-graph-ai

# Copy environment template and customize (optional)
cp env.template .env
# Edit .env with your configuration if needed
# Most defaults work for local development

# Start the API server
docker-compose up ohm-api

# Or run in detached mode (background)
docker-compose up -d ohm-api

# View logs
docker-compose logs -f ohm-api

# Stop the server
docker-compose down

# Access the API documentation at:
# http://localhost:8001/docs
```

**Docker Compose Benefits:**
- ✅ Consistent environment across all machines
- ✅ Automatic dependency management
- ✅ Easy volume management for storage and logs
- ✅ Built-in health checks
- ✅ Simple scaling and service management
- ✅ No need to install Python dependencies locally

#### Option 2: Local Development (For Active Development)

Use this option if you need to modify code frequently and want hot-reload without rebuilding Docker images.

```bash
# Clone the repository
git clone https://github.com/helpfulengineering/supply-graph-ai.git
cd supply-graph-ai

# Create and activate conda environment
conda create -n supply-graph-ai python=3.10
conda activate supply-graph-ai

# Install dependencies
pip install -r requirements.txt

# Install the package in editable mode (creates 'ohm' command)
pip install -e .

# Verify installation
ohm --help

# Start the API server with hot-reload
python run.py

# Or use uvicorn directly for more control
uvicorn src.core.main:app --reload --host 0.0.0.0 --port 8001

# Or use the CLI directly
ohm system health
```

#### Option 3: Local Development (Legacy - without package installation)

```bash
# Clone the repository
git clone https://github.com/helpfulengineering/supply-graph-ai.git
cd supply-graph-ai

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install spaCy language model (required for NLP matching)
python -m spacy download en_core_web_md
```

## Documentation

This README provides a quick start guide and basic project information. For documentation, please build the documentation locally.

### Building Documentation Locally

The OHM documentation is built using [MkDocs](https://www.mkdocs.org/), a simple static site generator for project documentation.

To build and view the documentation locally:

1. Install MkDocs and required plugins:
```bash
pip install mkdocs mkdocs-material mkdocs-mermaid2-plugin
```

2. Start the documentation server:
```bash
mkdocs serve
```

4. Open your browser to `http://localhost:8000/` (Note: This is the MkDocs documentation server port, not the API server which runs on port 8001)

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
open-matching-engine/
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
├── pyproject.toml          # Package configuration (creates 'ohm' command via pip install -e .)
├── requirements.txt        # Project dependencies
└── run.py                  # FastAPI server on uvicorn
```

## Running the Application

### Using Docker (Recommended)

```bash
# Start the API server
docker-compose up ohm-api

# Or run CLI commands
docker run --rm \
  -v $(pwd)/test-data:/app/test-data \
  open-matching-engine cli okh validate /app/test-data/manifest.okh.json

# Access the API documentation at:
# http://localhost:8001/docs
```

### Local Development

Note: You may need to add a directory called "logs" locally if the command below indicates it can't open the log file!

```bash
# Start the FastAPI server
python run.py

# Visit the API documentation at:
# http://127.0.0.1:8001/v1/docs
```

For container deployment guides, see the [Container Guide](docs/development/container-guide.md) in our documentation.
