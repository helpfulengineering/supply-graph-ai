# Open Hardware Manager API

## Introduction

The Open Hardware Manager (OHM) API provides programmatic access to match requirements with capabilities across multiple domains and generate valid solutions represented as Supply Trees. This document describes the **standardized API** (error handling, LLM integration patterns, and response shapes). **Do not treat the narrative sections below as an exhaustive route catalog** — paths change with releases. With the API running, use **`/v1/docs`** (Swagger UI) and **`/v1/openapi.json`** as the source of truth. A **generated** operation table lives under [Routes and Endpoints](#routes-and-endpoints); refresh it with `uv run python scripts/generate_openapi_routes_md.py`. Router wiring for `api_v1` is in `src/core/main.py`. For a machine-readable refresh checklist, see [Conference demo readiness](../development/conference-demo-readiness.md#api-machine-truth-refresh-before-demo).

**Supported Domains:**
- **Manufacturing Domain**: Match OKH requirements with OKW capabilities
- **Cooking Domain**: Match recipe requirements with kitchen capabilities

## Architecture Overview

The API is structured around core domain models:

1. **OpenKnowHow (OKH)** - Represents hardware design specifications and requirements (Manufacturing Domain)
2. **OpenKnowWhere (OKW)** - Represents manufacturing capabilities and facilities (Manufacturing Domain)
3. **Recipes** - Represents cooking requirements (Cooking Domain)
4. **Kitchens** - Represents cooking capabilities and facilities (Cooking Domain)
5. **Supply Trees** - Represents valid solutions matching requirements with capabilities across all domains

Each domain has its own set of routes for creation, validation, retrieval, and specialized operations. The API follows RESTful principles with **standardized response formats**, **error handling**, **LLM integration support**, and appropriate status codes.

### API Model Architecture

The API uses a **consolidated model architecture** with:

- **Unified Request/Response Models**: All endpoints use standardized base classes (`BaseAPIRequest`, `SuccessResponse`) with proper inheritance
- **LLM Integration Ready**: All models inherit from `LLMRequestMixin` and `LLMResponseMixin` for seamless AI integration
- **Proper Separation of Concerns**: Request models in `request.py` files, response models in `response.py` files
- **No Model Duplication**: Single source of truth for each model, eliminating "Enhanced" prefixes and redundant definitions
- **Type Safety**: Full Pydantic validation and serialization across all endpoints

## API Versioning

All routes are prefixed with `/v1` to enable future versioning. This approach allows for introducing breaking changes in future versions without disrupting existing clients.

```
/v1/api/okh/...
/v1/api/okw/...
/v1/api/match/...
/v1/api/llm/...
```

Future versions would be accessible via `/v2`, `/v3`, etc., with the previous versions maintained for backward compatibility as needed.

## Storage Integration

The OHM API includes  storage integration with Azure Blob Storage:

### Azure Blob Storage Features
- **Automatic OKW Loading**: The `/v1/api/match` endpoint automatically loads all OKW facilities from the configured Azure container
- **File Format Support**: Supports both YAML and JSON file formats for OKW facilities
- **Real-time Processing**: Processes files from storage in real-time during matching operations
- **Domain Handlers**: Specialized storage handlers for different data types (OKH, OKW, supply trees)

### Storage Configuration
The system uses environment variables for Azure storage configuration:
- `AZURE_STORAGE_ACCOUNT`: Azure storage account name
- `AZURE_STORAGE_KEY`: Azure storage account key
- `AZURE_STORAGE_CONTAINER`: Container name for OKW facilities

### File Processing
- **Automatic Parsing**: YAML and JSON files are automatically parsed and converted to `ManufacturingFacility` objects
- **Error Handling**: Invalid files are logged and skipped, allowing the system to continue processing
- **Filtering**: OKW facilities can be filtered by location, capabilities, access type, and facility status

## Standardized Error Handling

All API routes use an error handling system with:

### Error Response Format
```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid input data",
    "details": {
      "field": "title",
      "issue": "Required field is missing"
    },
    "suggestion": "Please provide a valid title for the resource",
    "request_id": "req_123456789"
  }
}
```

### Success Response Format
```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Example Resource"
  },
  "metadata": {
    "processing_time": 0.042
  }
}
```

### Error Types
- **Validation Errors (422)**: Invalid input data with field-specific guidance
- **Not Found Errors (404)**: Resource not found with helpful suggestions
- **Server Errors (500)**: Internal errors with support contact information
- **Authentication Errors (401)**: Authentication required with login guidance
- **Authorization Errors (403)**: Insufficient permissions with role information

## Authentication and Authorization

The API requires authentication for all routes except public read operations. Authentication is implemented using API keys passed in the `Authorization` header:

```
Authorization: Bearer {api_key}
```

Authorization is role-based with the following permission levels:
- **Read** - Access to GET operations
- **Write** - Access to POST/PUT operations
- **Admin** - Full access including DELETE operations

## Routes and Endpoints

The canonical **method + path + request/response schema** inventory is generated from the mounted FastAPI app (`api_v1`) OpenAPI document.

- **Interactive:** with the API running, open `{base}/v1/docs` and `{base}/v1/openapi.json` (substitute your host and port for `{base}`, e.g. `http://localhost:8001`).
- **Regenerate the table below** (from the repository root):  
  `uv run python scripts/generate_openapi_routes_md.py`

### Generated route inventory

--8<-- "docs/api/_generated/openapi-route-table.md"

The headings below are **stub anchors** so other docs can deep-link here; full request/response detail is in the table above and in **`/v1/docs`**.

### OKH Routes

### OKW Routes

### Validation and Normalization

### Supply Tree Routes

### Domain Management Routes

### File Upload

### Export Schema

### Taxonomy Routes

### System Routes

### Rules Management Routes

## Error Responses

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "resource_not_found",
    "message": "The requested resource was not found",
    "details": {
      "resource_type": "okh",
      "resource_id": "123"
    }
  }
}
```

Common HTTP status codes:
- 200: OK
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Unprocessable Entity
- 500: Internal Server Error

## Pagination

List endpoints support pagination with consistent parameters:

- `page`: Page number (default: 1)
- `page_size`: Results per page (default: 20, max: 100)

Paginated responses include consistent metadata:

```json
{
  "results": [...],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

## Standardized Response Patterns

### Success Response Structure
All successful API responses follow this standardized format:

```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789",
  "data": {
    // Response data here
  },
  "metadata": {
    "processing_time": 0.123
  }
}
```

### Error Response Structure
All error responses follow this standardized format:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid input data",
    "details": {
      "field": "title",
      "issue": "Required field is missing"
    },
    "suggestion": "Please provide a valid title for the resource",
    "request_id": "req_123456789",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### LLM Integration Response Structure
Routes with LLM integration include additional metadata under `metadata`:

```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123456789",
  "data": {
    // Response data here
  },
  "metadata": {
    "processing_time": 1.23,
    "llm_metadata": {
      "provider": "anthropic",
      "model": "claude-3-sonnet",
      "quality_level": "professional",
      "tokens_used": 150
    }
  }
}
```

## Core API Usage Patterns

#### **Matching OKH Requirements to OKW Capabilities**

**Basic Matching:**
```python
import httpx

async def match_requirements():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/v1/api/match",
            json={
                "okh_manifest": {
                    "title": "CNC Machined Bracket",
                    "manufacturing_processes": ["CNC", "Deburring"],
                    # ... other required fields
                }
            }
        )
        return response.json()
```

**Matching with Filters:**
```python
async def match_with_filters():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/v1/api/match",
            json={
                "okh_manifest": okh_data,
                "okw_filters": {
                    "access_type": "Restricted",
                    "facility_status": "Active"
                }
            }
        )
        return response.json()
```

**Matching against the unified network (local ∪ Maps of Making):**

Pass `network_filter` to match a design against the same filtered network the
browse surface (`GET /api/okw/spaces`) shows — local OKW facilities unioned with
Maps of Making spaces, narrowed by the given filters. MoM spaces match at the
process level (they have no equipment detail), surfacing "spaces that claim these
processes — worth contacting". Equivalent CLI: `ohm match requirements … --network --network-country FR`.

```python
async def match_against_network():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/v1/api/match",
            json={
                "okh_id": "…",
                "network_filter": {"include_mom": True, "country": "FR", "process": "laser_cutting"},
            },
        )
        return response.json()
```

**Matching against a chosen subset of facilities:**

Pass `okw_ids` to restrict matching to specific facilities the caller has already
selected (for example, from the OKW catalog). Facilities are still loaded from the
configured source, then filtered to these IDs before matching; an empty or omitted
list matches against all facilities. Equivalent CLI: `ohm match ... --okw-id <id> --okw-id <id>`.

```python
async def match_selected_facilities():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/v1/api/match",
            json={
                "okh_id": "…",
                "okw_ids": ["okw-1", "okw-2", "okw-3"],
            },
        )
        return response.json()
```

**Reverse matching (designs a facility can produce):**

`POST /api/match/facility` is the inverse of `POST /api/match`: given an OKW
facility, it returns the OKH designs that facility can produce, ranked by
confidence. It evaluates every design in the catalog against the single facility
using the same matching logic. Equivalent CLI: `ohm match facility <okw-id>`.

```python
async def designs_for_facility():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/v1/api/match/facility",
            json={"okw_id": "…", "min_confidence": 0.1, "max_results": 10},
        )
        return response.json()  # data.designs[] = [{okh_id, okh_title, confidence, rank}]
```

**Matching from URL:**
```python
async def match_from_url():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/v1/api/match",
            json={
                "okh_url": "https://raw.githubusercontent.com/example/okh.yaml"
            }
        )
        return response.json()
```

#### **OKW Facility Management**

**List All Facilities:**
```python
async def list_facilities():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8001/v1/api/okw")
        return response.json()
```

**Search Facilities:**
```python
async def search_facilities():
    async with httpx.AsyncClient() as client:
        # Search by access type
        response = await client.get(
            "http://localhost:8001/v1/api/okw/search",
            params={"access_type": "Membership"}
        )
        
        # Search by multiple criteria
        response = await client.get(
            "http://localhost:8001/v1/api/okw/search",
            params={
                "access_type": "Restricted",
                "facility_status": "Active",
                "location": "United States"
            }
        )
        return response.json()
```

### Multi-Layered Matching System

The matching system uses a sophisticated multi-layered approach with detailed metadata tracking and confidence scoring:

#### **Layer 1: Direct Matching (Advanced)**
- **Case-insensitive exact string matching** with defensive confidence scoring
- **Near-miss detection** using Levenshtein distance (≤2 character differences)
- ** metadata tracking** including match quality indicators
- **Confidence penalties** for case/whitespace differences
- **Domain-agnostic base class** with domain-specific implementations

**Match Types:**
- **Perfect Match** (confidence: 1.0): Exact case and whitespace match
- **Case Difference** (confidence: 0.95): Case-insensitive exact match
- **Near Miss** (confidence: 0.8): ≤2 character differences (e.g., "CNC" ↔ "CNC mill")
- **No Match** (confidence: 0.0): >2 character differences

**Example Matches:**
- "CNC" ↔ "CNC" (perfect match)
- "CNC" ↔ "cnc" (case difference)
- "CNC" ↔ "CNC mill" (near miss)
- "CNC" ↔ "3D Printing" (no match)

#### **Layer 2: Heuristic Matching**
- Rule-based matching with synonyms and abbreviations
- Matches: "CNC" ↔ "Computer Numerical Control"
- Matches: "3D Printing" ↔ "Additive Manufacturing"

#### **Supported Heuristic Rules**
```python
HEURISTIC_RULES = {
    # Abbreviations
    "cnc": ["computer numerical control", "computer numerical control machining"],
    "cad": ["computer aided design", "computer-aided design"],
    "cam": ["computer aided manufacturing", "computer-aided manufacturing"],
    
    # Process synonyms
    "additive manufacturing": ["3d printing", "3-d printing", "rapid prototyping"],
    "subtractive manufacturing": ["cnc machining", "machining", "material removal"],
    
    # Material synonyms
    "stainless steel": ["304 stainless", "316 stainless", "ss", "stainless"],
    "aluminum": ["al", "aluminium", "aluminum alloy"],
}
```

### Storage Integration

#### **Azure Blob Storage Configuration**
```bash
# Environment variables
AZURE_STORAGE_ACCOUNT=your_storage_account
AZURE_STORAGE_KEY=your_storage_key
AZURE_STORAGE_CONTAINER=okw
```

#### **Supported File Formats**
- **YAML**: `.yaml`, `.yml` files
- **JSON**: `.json` files

#### **File Structure**
OKW files should contain `ManufacturingFacility` data:
```yaml
id: "12345678-1234-1234-1234-123456789abc"
name: "Professional Machine Shop"
location:
  address:
    street: "123 Main St"
    city: "Manufacturing City"
    country: "United States"
facility_status: "Active"
access_type: "Restricted"
manufacturing_processes:
  - "https://en.wikipedia.org/wiki/CNC_mill"
  - "https://en.wikipedia.org/wiki/CNC_lathe"
equipment: []
typical_materials: []
```

### Error Handling

#### **Common Error Responses**
```json
{
  "detail": "Error message describing what went wrong"
}
```

#### **HTTP Status Codes**
- `200`: Success
- `400`: Bad Request (invalid input)
- `404`: Not Found
- `500`: Internal Server Error

## Advanced Validation Framework

The OHM API includes a  validation framework that provides domain-aware validation with quality levels and  error reporting.

### Validation Features

#### **Quality Levels**
All validation endpoints support three quality levels:

- **Hobby Level**: Relaxed validation for personal projects and makerspaces
  - Basic required fields only
  - Warnings for missing optional fields
  - Suitable for prototyping and personal use

- **Professional Level**: Standard validation for commercial use
  - Additional required fields for production readiness
  -  validation rules
  - Suitable for commercial manufacturing

- **Medical Level**: Strict validation for medical device manufacturing
  - Highest validation standards
  - Regulatory compliance requirements
  - Quality standards and certifications required

#### **Strict Mode**
Optional strict validation mode that:
- Treats warnings as errors
- Enforces additional validation rules
- Provides maximum validation coverage

#### ** Error Reporting**
Validation responses include:
- **Severity Levels**: `error`, `warning`, `info`
- **Field Paths**: Exact location of validation issues
- **Error Codes**: Standardized error codes for programmatic handling
- **Completeness Scores**: Quantitative assessment of data completeness

### Validation Endpoints

#### **OKH Validation** (`POST /v1/api/okh/validate`)
- Domain: Manufacturing
- Quality Levels: `hobby`, `professional`, `medical`
- Validates OKH manifest structure and completeness
- Returns detailed validation results with field-specific errors

#### **OKW Validation** (`POST /v1/api/okw/validate`)
- Domain: Manufacturing
- Quality Levels: `hobby`, `professional`, `medical`
- Validates OKW facility structure and capabilities
- Validates equipment specifications and manufacturing processes

#### **Supply Tree Validation** (`POST /v1/api/match/validate`)
- Domain: Manufacturing
- Quality Levels: `hobby`, `professional`, `medical`
- Validates supply tree workflows and resource requirements
- Validates OKH/OKW references and compatibility

### Example Usage

```python
import httpx

async def validate_okh():
    async with httpx.AsyncClient() as client:
        # Professional level validation
        response = await client.post(
            "http://localhost:8001/v1/api/okh/validate?quality_level=professional",
            json={
                "content": {
                    "title": "CNC Bracket",
                    "version": "1.0.0",
                    "license": {"hardware": "MIT"},
                    "licensor": "Test User",
                    "documentation_language": "en",
                    "function": "Support bracket for CNC machine"
                }
            }
        )
        result = response.json()
        
        if result["valid"]:
            print(f"Validation passed with {result['completeness_score']:.2f} completeness")
        else:
            for issue in result["issues"]:
                print(f"{issue['severity'].upper()}: {issue['message']} at {issue['path']}")

# Strict mode validation
async def validate_strict():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/v1/api/okh/validate?quality_level=medical&strict_mode=true",
            json={"content": okh_data}
        )
        return response.json()
```

## LLM API Endpoints

The OHM API includes LLM (Large Language Model) integration for enhanced OKH manifest generation and facility matching. LLM functionality is primarily integrated into domain-specific endpoints (e.g., `/v1/api/match`, `/v1/api/okh/generate-from-url`) via the `@llm_endpoint` decorator.

For direct LLM operations, use the CLI commands (`ohm llm generate`, `ohm llm generate-okh`). The API provides monitoring and discovery endpoints for LLM service management.

### LLM Health Check

**Endpoint:** `GET /v1/api/llm/health`

Check LLM service health and provider status.

**Response:**
```json
{
  "status": "success",
  "message": "LLM service health check completed",
  "timestamp": "2024-01-01T12:00:00Z",
  "health_status": "healthy",
  "providers": {
    "anthropic": {
      "name": "anthropic",
      "type": "anthropic",
      "status": "healthy",
      "model": "claude-sonnet-4-5-20250929",
      "is_connected": true,
      "available_models": ["claude-sonnet-4-5-20250929", "claude-3-5-sonnet-latest"]
    },
    "openai": {
      "name": "openai",
      "type": "openai",
      "status": "error",
      "error": "Provider not initialized"
    }
  },
  "metrics": {
    "total_requests": 150,
    "total_cost": 0.45,
    "average_cost_per_request": 0.003,
    "active_provider": "anthropic",
    "available_providers": ["anthropic"]
  }
}
```

**Status:**  **Fully Implemented** - LLM service health check with provider status

### Get Available Providers

**Endpoint:** `GET /v1/api/llm/providers`

List all configured LLM providers and their status.

**Response:**
```json
{
  "status": "success",
  "message": "Providers retrieved successfully",
  "timestamp": "2024-01-01T12:00:00Z",
  "providers": [
    {
      "name": "anthropic",
      "type": "anthropic",
      "status": "healthy",
      "model": "claude-sonnet-4-5-20250929",
      "is_connected": true,
      "available_models": ["claude-sonnet-4-5-20250929", "claude-3-5-sonnet-latest"]
    },
    {
      "name": "openai",
      "type": "openai",
      "status": "not_available",
      "error": "Provider not initialized"
    }
  ],
  "default_provider": "anthropic",
  "available_providers": ["anthropic"]
}
```

**Status:**  **Fully Implemented** - Provider discovery and status information

### Note on LLM Functionality

LLM capabilities are integrated into domain-specific endpoints:
- **OKH Generation**: `POST /v1/api/okh/generate-from-url` - Uses LLM for intelligent file categorization
- **Matching**: `POST /v1/api/match` - Supports LLM-enhanced matching via `@llm_endpoint` decorator
- **Metrics**: `GET /v1/api/utility/metrics` - Includes LLM usage metrics and costs

For direct LLM operations, use the CLI:
- `ohm llm generate` - Generic content generation
- `ohm llm generate-okh` - OKH manifest generation
- `ohm llm providers info` - Provider information

## API Documentation & Developer Experience

### Interactive Documentation
The OHM API provides  interactive documentation:

- **Root app** (top-level `app` only, if exposed): `http://localhost:8001/docs`
- **Versioned OHM API**: `http://localhost:8001/v1/docs` — Swagger UI for all `api_v1` operations
- **OpenAPI JSON** (`api_v1`): `http://localhost:8001/v1/openapi.json`

### Developer Features
- **Request Validation**:  input validation with detailed error messages
- **Type Safety**: Full Pydantic model validation and serialization
- **Error Handling**: Consistent error response format with helpful error messages
- **Async Support**: Full async/await support for high-performance operations
- **CORS Support**: Cross-origin resource sharing enabled for web applications

### Testing & Development
- **Health Check**: `GET /health` - System status and registered domains
- **Root Endpoint**: `GET /` - API information and navigation links
- **Hot Reload**: Development server with automatic reload on code changes
