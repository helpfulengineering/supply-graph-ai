# API Documentation

The Open Matching Engine (OME) provides both REST and Python APIs to interact with the matching engine. This section documents how to use these APIs, their design principles, and planned extensions.

## API Architecture Overview

OME uses [FastAPI](https://fastapi.tiangolo.com/) as its web framework.

FastAPI is a modern, fast (high-performance), web framework for building APIs with Python based on standard Python type hints.

The key features are:

- Fast: Very high performance, on par with NodeJS and Go.
- Intuitive: Great editor support. Completion everywhere. Less time debugging.
- Easy: Designed to be easy to use and learn. Less time reading docs.
- Robust: Get production-ready code. With automatic interactive documentation.
- Standards-based: Based on (and fully compatible with) the open standards for APIs: OpenAPI (previously known as Swagger) and JSON Schema.
- Automatic OpenAPI documentation generation
- Request validation with Pydantic models
- Modern async support
- Type hints and automatic serialization/deserialization

### Key Design Patterns

The API follows these key design patterns:

1. **Model-Route Separation**: Clear separation between data models (Pydantic) and route handlers
2. **Domain-Based Organization**: API endpoints organized by domains (cooking, manufacturing)
3. **Layered Architecture**: 
   - Routes (handling HTTP requests)
   - Services (business logic)
   - Repositories (data access)

## Available APIs

OME offers two main API interfaces:

1. [**REST API**](rest.md): HTTP-based API for integration with any client
2. [**Python API**](python.md): Direct Python interface for tighter integration

Both APIs offer the same core functionality with different integration patterns.

## Core API Concepts

### Supply Tree Generation

All APIs revolve around the core concept of generating and manipulating Supply Trees, which represent complete solutions matching requirements to capabilities.

### Domain-Specific Endpoints

Each supported domain (e.g., cooking, manufacturing) has dedicated endpoints optimized for domain-specific matching.

### Authentication

For production deployments, [authentication](auth.md) can be enabled to secure API access.

## API Roadmap

The OME API will be developed in phases:

### Phase 1: Core Matching (Current)

- Basic requirement-to-capability matching
- Simple domain registration
- Supply Tree generation and validation

### Phase 2: Enhanced Matching

- Multi-stage matching process
- Confidence scoring
- Alternative path generation
- Detailed validation feedback

### Phase 3: Advanced Features

- Real-time validation updates
- Collaborative editing of Supply Trees
- Matching optimization
- External system integration

### Phase 4: AI/ML Integration

- Machine learning for matching recommendations
- Natural language processing for unstructured inputs
- Pattern recognition for improved matches
- LLM-enhanced reasoning