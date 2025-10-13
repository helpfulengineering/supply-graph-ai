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



## Core API Concepts

### Supply Tree Generation

All APIs revolve around the core concept of generating and manipulating Supply Trees, which represent complete solutions matching requirements to capabilities.

### Domain-Specific Endpoints

Each supported domain (e.g., cooking, manufacturing) has dedicated endpoints optimized for domain-specific matching.

### Authentication

For production deployments, [authentication](auth.md) can be enabled to secure API access.

## Current API Status

The OME API is currently in **Phase 2: Enhanced Matching** with the following implemented features:

### ✅ Implemented Features

#### Core Matching Engine
- **Enhanced OKH Input Support**: Accept OKH manifests via inline JSON, storage ID reference, or remote URL
- **Flexible OKW Input Support**: 
  - **Cloud Storage Mode**: Automatically loads OKW facilities from Azure Blob Storage (production)
  - **Local Development Mode**: Accept inline OKW facilities for local development and testing
- **Advanced Filtering**: Filter OKW facilities by location, capabilities, access type, and facility status
- **Domain-Specific Extraction**: Uses registered domain extractors for requirements and capabilities
- **Supply Tree Generation**: Creates complete manufacturing solutions with confidence scoring

#### API Endpoints (19 total)
- **Match**: `/v1/match` - Enhanced matching with multiple input methods and filtering
- **OKH Management**: Create, validate, extract, and retrieve OKH manifests
- **OKW Management**: Create, search, validate, and retrieve OKW facilities  
- **Supply Tree Management**: Create, validate, and retrieve supply trees
- **Utility**: Domain listing and context information

#### Storage Integration
- **Azure Blob Storage**: Full integration with cloud storage for OKH/OKW data
- **File Format Support**: Automatic parsing of YAML and JSON files
- **Domain Handlers**: Specialized storage handlers for different data types

#### Documentation & Developer Experience
- **Interactive API Docs**: Full OpenAPI documentation at `/v1/docs`
- **Request Validation**: Comprehensive input validation with detailed error messages
- **Type Safety**: Full Pydantic model validation and serialization

### 🚧 Planned Features (Phase 3)

- Real-time validation updates
- Collaborative editing of Supply Trees
- Advanced matching optimization algorithms
- External system integration
- Batch processing capabilities

### 🔮 Future Features (Phase 4)

- Machine learning for matching recommendations
- Natural language processing for unstructured inputs
- Pattern recognition for improved matches
- LLM-enhanced reasoning