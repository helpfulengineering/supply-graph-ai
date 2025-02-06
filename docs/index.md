# Open Matching Engine (OME)

## Documentation Contents

### Core Concepts
* [System Overview](overview.md)
    * Core problem space
    * Project vision
    * Use cases
* [Architecture](architecture/index.md)
    * [System Components](architecture/components.md)
    * [Data Flow](architecture/data-flow.md)
    * [System Diagram](architecture/system-diagram.md)
    * [Storage and Caching](architecture/storage.md)
    * [Feedback System](architecture/feedback.md)

### Implementation Details
* [Data Models](models/index.md)
    * [Supply Trees](models/supply-tree.md)
    * [Process Requirements](models/process.md)
    * [Validation Contexts](models/validation.md)
* [Pipeline Components](pipelines/index.md)
    * [Extraction Pipeline](pipelines/extraction.md)
    * [Matching Pipeline](pipelines/matching.md)
    * [Validation Pipeline](pipelines/validation.md)
* [Domain Implementations](domains/index.md)
    * [Manufacturing Domain](domains/manufacturing.md)
        * OKH/OKW integration
        * Manufacturing-specific validation
    * [Cooking Domain](domains/cooking.md)
        * Recipe/Kitchen matching
        * Example implementations

### Developer Resources
* [Getting Started](getting-started/index.md)
    * [Installation](getting-started/installation.md)
    * [Basic Usage](getting-started/usage.md)
    * [Configuration](getting-started/configuration.md)
* [API Documentation](api/index.md)
    * [REST API](api/rest.md)
    * [Python API](api/python.md)
    * [Authentication](api/auth.md)
* [Contributing](contributing/index.md)
    * [Development Setup](contributing/setup.md)
    * [Code Style](contributing/style.md)
    * [Testing](contributing/testing.md)
    * [Documentation](contributing/documentation.md)

# Overview

The Open Matching Engine (OME) is a flexible, domain-agnostic framework designed to solve complex requirements-to-capabilities matching problems across various domains. At its core, OME helps answer the question: "Given a set of requirements, which available capabilities can fulfill them?"

## Key Features

### Supply Tree Generation
- Creates complete manufacturing solutions
- Handles multi-stage processes
- Supports parallel workflows
- Manages dependencies and constraints

### Context-Aware Validation
- Multiple validation contexts per requirement
- Context-specific acceptance criteria
- Detailed validation procedures
- Comprehensive failure handling

### Multi-Stage Processing
OME uses sophisticated multi-stage pipelines for both extraction and matching:

1. **Exact** - Direct, precise matches based on explicit criteria
2. **Heuristic** - Rule-based matching using domain knowledge
3. **NLP** - Natural language processing for semantic understanding
4. **AI/ML** - Machine learning and LLM-enhanced analysis for complex patterns

### Storage and Caching
- Permanent storage for validated data
- Cache layer for intermediate results
- Feedback system integration
- API-driven data access

## Getting Started

### For Users
If you're looking to use OME:

1. Start with our [Installation Guide](getting-started/installation.md)
2. Review the [Basic Usage Guide](getting-started/usage.md)
3. Explore our [API Documentation](api/index.md)

### For Developers
If you want to contribute to OME:

1. Set up your [Development Environment](contributing/setup.md)
2. Review our [Code Style Guide](contributing/style.md)
3. Learn about our [Testing Requirements](contributing/testing.md)
4. Check our [Documentation Guidelines](contributing/documentation.md)

## Project Status

OME is currently in active development with a focus on:

1. Core framework implementation
2. Supply Tree validation system
3. Context-aware matching
4. Domain-specific implementations

## Future Development

Planned enhancements include:

1. Advanced routing optimization
2. Extended validation contexts
3. Machine learning integration
4. Additional domain support
