# Open Matching Engine (OME)

## Overview

The Open Matching Engine (OME) is a flexible, domain-agnostic framework designed to solve complex requirements-to-capabilities matching problems across various domains. The system matches requirements (what needs to be done) with capabilities (what can be done) to create viable solutions.


## Quick Start for Developers

### Installation

#### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/helpfulengineering/supply-graph-ai.git
cd supply-graph-ai

# Copy environment template
cp env.template .env
# Edit .env with your configuration

# Start the API server
docker-compose up ome-api

# Access the API documentation at:
# http://localhost:8001/docs
```

#### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/helpfulengineering/supply-graph-ai.git
cd supply-graph-ai

# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Documentation

This README provides a quick start guide and basic project information. For documentation, please build the documentation locally.

### Building Documentation Locally

The OME documentation is built using [MkDocs](https://www.mkdocs.org/), a simple static site generator for project documentation.

To build and view the documentation locally:

1. Install MkDocs and required plugins:
```bash
pip install mkdocs mkdocs-material mkdocs-mermaid2-plugin
```

2. Start the documentation server:
```bash
mkdocs serve
```

4. Open your browser to `http://localhost:8000/`

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
├── src/                    # Source code
│   ├── core/               # Core framework components
│   │   ├── api/            # API endpoints
│   │   ├── domains/        # Domain implementations
│   │   ├── matching/       # Matching Rules Manager
│   │   ├── models/         # Data models
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
├── ome                     # Entrypoint for CLI
├── requirements.txt        # Project dependencies
└── run.py                  # FastAPI server on uvicorn
```

## Running the Application

### Using Docker (Recommended)

```bash
# Start the API server
docker-compose up ome-api

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


# Our current working OKH and OKW libraries
Our current OKH and OKW libraries are implemented as publicly accessible Azure blob containers:

    "Azure_Storage_ServiceName": "https://projdatablobstorage.blob.core.windows.net",
    "Azure_Storage_OKH_ContainerName": "okh",
    "Azure_Storage_OKW_ContainerName": "okw"
These OKHs and OKWs are taken from our repo: https://github.com/helpfulengineering/library.

Helpful created its own OKW template, and added an extenstion to OKH, both of which are defined here: https://github.com/helpfulengineering/OKF-Schema

We are currently working with the Internet of Production Alliance (IoPA) to unify these extensions with their official schemas.

