# Open Matching Engine (OME)

## Overview

The Open Matching Engine (OME) is a flexible, domain-agnostic framework designed to solve complex requirements-to-capabilities matching problems across various domains. The system matches requirements (what needs to be done) with capabilities (what can be done) to create viable solutions.

## Current Development Status

- **Phase**: Proof of Concept / MVP
- **Primary Domain**: Cooking (for concept validation)
- **Target Domain**: Manufacturing (OKH/OKW integration)

## Quick Start for Developers

### Prerequisites

- Python 3.8+
- FastAPI
- NetworkX
- Pydantic
- PyYAML

### Installation

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

This README provides a quick start guide and basic project information. For comprehensive documentation, please build the documentation locally.

### Building Documentation Locally

The OME documentation is built using [MkDocs](https://www.mkdocs.org/), a fast and simple static site generator that's excellent for project documentation.

To build and view the documentation locally:

1. Install MkDocs and required plugins:
```bash
pip install mkdocs mkdocs-material mkdocs-mermaid2-plugin
```

2. Start the documentation server:
```bash
mkdocs serve
```

4. Open your browser to `http://127.0.0.1:8000`

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
│   │   ├── models/         # Data models
│   │   ├── registry/       # Domain registry
│   │   └── services/       # Core services
│   └── utils/              # Utility functions
├── tests/                  # Test cases
├── mkdocs.yml              # Documentation configuration
└── requirements.txt        # Project dependencies
```

## Running the Application Locally

```bash
# Start the FastAPI server
python run.py

# Visit the API documentation at:
http://127.0.0.1:8000/docs
```

