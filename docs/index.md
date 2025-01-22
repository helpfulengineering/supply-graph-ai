# Open Matching Engine (OME)

## Documentation Contents

* [Architecture](architecture.md) - System architecture and design principles
    * [System Diagram](system-diagram.md) - High-level system architecture visualization
    * [Data Flow Diagram](data-flow-diagram.md) - Detailed data flow between components
* [Domain Implementations](domains/)
    * [Manufacturing Domain](domains/manufacturing.md) - Implementation details for OKH/OKW matching
    * [Cooking Domain](domains/cooking.md) - Implementation details for recipe/kitchen matching
* [API Documentation](api/) - API reference and usage guides

# Overview

The Open Matching Engine (OME) is a flexible, domain-agnostic framework designed to solve complex requirements-to-capabilities matching problems across various domains. At its core, OME helps answer the question: "Given a set of requirements, which available capabilities can fulfill them?"

## Core Concepts

### Multi-Stage Processing

OME uses a sophisticated multi-stage approach for both extraction and matching:

1. **Exact** - Direct, precise matches based on explicit criteria
2. **Heuristic** - Rule-based matching using domain knowledge
3. **NLP** - Natural language processing for semantic understanding
4. **AI/ML** - Machine learning and LLM-enhanced analysis for complex patterns

Each stage builds upon the previous ones, progressively improving match quality while maintaining clear confidence scoring.

### Domain Flexibility

While OME can be applied to many domains, we currently focus on two main use cases:

- **Manufacturing** - Matching hardware designs (OKH) with manufacturing capabilities (OKW)
- **Cooking** - Matching recipes with available kitchen equipment and ingredients

These domains serve as proof-of-concept implementations while we develop the core framework.

## Getting Started

### For Users

If you're looking to use OME:

1. Check out our [Architecture Overview](architecture.md) to understand the system
2. Review the [Data Models](data_models.md) to see how information flows
3. Explore our domain-specific implementations:
   - [Manufacturing Domain](domains/manufacturing.md)
   - [Cooking Domain](domains/cooking.md)

### For Contributors

If you want to contribute to OME:

1. Familiarize yourself with our base abstractions in `src/core`
2. Review domain implementations in `src/domains`
3. Check our [Contributing Guidelines](CONTRIBUTING.md)

## Project Status

OME is currently in early development with a focus on:

1. Core framework implementation
2. Proof-of-concept domains
3. API development
4. Documentation

## Vision

Our goal is to create a robust, extensible system that can:

- Parse unstructured or semi-structured input
- Extract meaningful, structured information
- Match requirements against available capabilities
- Support multiple domains with a consistent architectural approach

By providing these capabilities in an open-source framework, we aim to enable better discovery and utilization of resources across various domains.

## Learn More

- [Architecture](architecture.md) - Detailed system design
- [Data Models](data_models.md) - How we structure information
- [Domains](domains/) - Domain-specific implementations
- [API Documentation](api/) - Using OME programmatically

## Get Involved

We welcome contributions! Here's how you can help:

- Review our documentation
- Test domain implementations
- Add new domains
- Improve matching algorithms
- Report issues and suggest features

See our [Contributing Guidelines](CONTRIBUTING.md) for more information.