# Open Matching Engine (OME)

## Overview

The Open Matching Engine (OME) is a flexible, domain-agnostic framework designed to solve complex requirements-to-capabilities matching problems across various domains.

## Documentation

This README provides a quick start guide and basic project information. For comprehensive documentation, please build the documentation locally.

### Building Documentation Locally

The OME documentation is built using [MkDocs](https://www.mkdocs.org/), a fast and simple static site generator that's excellent for project documentation.

To build and view the documentation locally:

1. Install MkDocs and required plugins:
```bash
pip install mkdocs mkdocs-material mkdocs-mermaid2-plugin
```

2. Clone the repository:
```bash
git clone https://github.com/helpfulengineering/supply-graph-ai.git
cd open-matching-engine
```

3. Start the documentation server:
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

## Quick Start

### Prerequisites

- Python 3.8+
- Dependencies (list to be defined)

### Installation

```bash
# Clone the repository
git clone https://github.com/helpfulengineering/supply-graph-ai

# Install dependencies
pip install -r requirements.txt
```

## Current Development Status

- **Phase**: Proof of Concept
- **Primary Domain**: Cooking
- **Target Domain**: Manufacturing


## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:
- Code of conduct
- Development workflow
- Pull request process
- Testing requirements

