# Open Hardware Manager (OHM)

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
    * [Matching Architecture](architecture/matching.md)
    * [Generation](architecture/generation.md)
    * [Services](architecture/services.md)
* [Cheatsheet](cheatsheet.md)

### Development Plans
* [Developer Guide](development/developer-guide.md)

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

### Project Scaffolding
* [Scaffolding Guide](scaffolding/index.md)
    * [Quick Start](scaffolding/quick-start.md)
    * Generate OKH-compliant project structures
    * MkDocs integration and documentation templates

### Format Conversion
* [Conversion](conversion/index.md)
    * [MSF Datasheet](conversion/msf-datasheet.md)

### CLI Documentation
* [CLI Documentation](CLI/index.md)
    * [Quick Start Guide](CLI/quick-start.md)
    * [Examples](CLI/examples.md)
    * [Architecture](CLI/architecture.md)

### LLM Service Documentation
* [LLM Main Documentation](llm/index.md)
* [LLM Service Documentation](llm/llm-service.md)
    * Complete API and CLI reference
    * Configuration and setup guide
    * Integration examples and best practices
* [LLM Quick Start Guide](llm/llm-quick-start.md)
    * Get started in 5 minutes
    * Common commands and troubleshooting
    * Developer tips and monitoring
* [LLM Config](llm/configuration.md)
* [LLM API](llm/api.md)
* [LLM CLI](llm/cli.md)
* [LLM Generation](llm/generation.md)

### Matching System
* [Matching Layers Architecture](architecture/matching.md)
    * [Direct Matching Layer](matching/direct-matching.md)
    * [Capability-Centric Heuristic Rules](matching/heuristic-matching.md)

# Overview

The Open Hardware Manager (OHM) is a flexible, domain-agnostic framework designed to solve complex requirements-to-capabilities matching problems across various domains. At its core, OHM helps answer the question: "Given a set of requirements, which available capabilities can fulfill them?"

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
- Failure handling

### Multi-Stage Processing
OHM uses sophisticated multi-stage pipelines for both extraction and matching:

1. **Direct** - Exact string matching with near-miss detection
2. **Heuristic** - Rule-based matching using domain knowledge
3. **NLP** - Natural language processing for semantic understanding
4. **LLM** - Large Language Model integration for advanced reasoning and analysis

### Storage and Caching
- Permanent storage for validated data
- Cache layer for intermediate results
- Feedback system integration
- API-driven data access

### Command Line Interface
- CLI with 39 commands across 7 command groups
- **LLM Integration**: AI-powered generation and matching commands
- HTTP API integration with automatic fallback to direct service calls
- Package management (build, push, pull, verify)
- System administration and monitoring
- Multiple output formats (text, JSON, table)
- Robust error handling and user-friendly messages

## Getting Started

### For Users
If you're looking to use OHM:

1. Start with our [CLI Quick Start Guide](CLI/quick-start.md)
2. Try the [LLM Quick Start Guide](llm/llm-quick-start.md) for AI-powered features
3. Check out the [Project Overview](overview.md)
4. Explore our [CLI Documentation](CLI/index.md)
5. Review our [API Documentation](api/index.md)

### For Developers
If you're developing with OHM:

1. Read the [Developer Guide](development/developer-guide.md)
2. Check the [LLM Service Documentation](llm/llm-service.md) for AI integration
3. Review the [Architecture Documentation](architecture/index.md)
4. Explore the [Data Models](models/index.md)
