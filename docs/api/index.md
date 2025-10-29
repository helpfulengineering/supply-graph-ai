# API Documentation

The Open Matching Engine (OME) provides a comprehensive REST API built on FastAPI with complete standardization, enterprise-grade error handling, and LLM integration support. This section documents the fully standardized API system with 43 routes across 6 command groups, all with comprehensive testing and production readiness.

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

The API follows these standardized design patterns:

1. **Model-Route Separation**: Clear separation between data models (Pydantic) and route handlers
2. **Domain-Based Organization**: API endpoints organized by domains (cooking, manufacturing)
3. **Standardized Error Handling**: Consistent error responses with helpful suggestions
4. **LLM Integration Ready**: All routes support LLM request/response mixins
5. **Performance Tracking**: Built-in metrics and request tracking
6. **Layered Architecture**: 
    - Routes (handling HTTP requests with standardized patterns)
    - Services (business logic with BaseService patterns)
    - Repositories (data access with standardized interfaces)



## Core API Concepts

### Authentication

For production deployments, [authentication](auth.md) can be enabled to secure API access.

## Current API Status

### ✅ Implemented Features

#### Core Matching Engine
- **Enhanced OKH Input Support**: Accept OKH manifests via inline JSON, storage ID reference, or remote URL
- **Flexible OKW Input Support**: 
  - **Cloud Storage Mode**: Automatically loads OKW facilities from Azure Blob Storage (production)
  - **Local Development Mode**: Accept inline OKW facilities for local development and testing
- **Advanced Filtering**: Filter OKW facilities by location, capabilities, access type, and facility status
- **Domain-Specific Extraction**: Uses registered domain extractors for requirements and capabilities
- **Supply Tree Generation**: Creates complete manufacturing solutions with confidence scoring

#### API Endpoints (43 total - Fully Standardized)
- **Match Routes (7)**: Enhanced matching with multiple input methods, filtering, and LLM support
- **OKH Routes (9)**: Complete CRUD operations with validation, extraction, and LLM integration
- **OKW Routes (9)**: Complete CRUD operations with search, validation, and LLM integration
- **Package Routes (10)**: Package building, verification, and management with LLM support
- **Supply Tree Routes (6)**: Supply tree creation, validation, and management
- **Utility Routes (2)**: Domain listing and context information with LLM analysis

#### Storage Integration
- **Azure Blob Storage**: Full integration with cloud storage for OKH/OKW data
- **File Format Support**: Automatic parsing of YAML and JSON files
- **Domain Handlers**: Specialized storage handlers for different data types

#### Standardized Error Handling & Response Format
- **Consistent Error Responses**: All routes use `create_error_response` and `create_success_response`
- **Helpful Error Messages**: Clear, actionable error messages with suggestions
- **Request Tracking**: All responses include request IDs for debugging
- **Validation Errors**: Comprehensive validation with field-specific error reporting

#### Documentation & Developer Experience
- **Interactive API Docs**: Full OpenAPI documentation at `/v1/docs`
- **Request Validation**: Comprehensive input validation with detailed error messages
- **Type Safety**: Full Pydantic model validation and serialization
- **LLM Integration**: All routes support LLM request/response mixins
- **Performance Tracking**: Built-in metrics and request monitoring
