# Open Matching Engine (OME)

## Documentation Contents

### Core Concepts
* [System Overview](overview.md)
    * Core problem space
    * Project vision
    * Use cases
* [Architecture](architecture/index.md)
    * [Storage](architecture/storage.md)
    * [Data Flow Diagram](architecture/data-flow-diagram.md)
    * [System Diagram](architecture/system-diagram.md)
    * [Workflow Generation](architecture/workflow-generation.md)

### Development Plans
* [Getting Started](development/getting-started.md)
* [OME MVP Plan](development/ome-mvp-plan.md)
* [Domain Management](development/domain-management.md)

### Data Models
* [Data Models](models/index.md)
    * [Supply Trees](models/supply-tree.md)
    * [Bill of Materials](models/bom.md)
    * [Process Requirements](models/process.md)
    * [Validation Contexts](models/validation.md)
    * [Open Know How](models/okh-docs.md)
    * [Open Know Where](models/okw-docs.md)
* [Domain Implementations](domains/index.md)
    * [Manufacturing Domain](domains/manufacturing.md)
    * [Cooking Domain](domains/cooking.md)

### API Documentation
* [API Documentation](api/index.md)
    * [Routes & Endpoints](api/routes.md)
    * [Authentication](api/auth.md)

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

1. Start with our [Installation Guide](development/getting-started.md)
2. Explore our [API Documentation](api/index.md)


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
