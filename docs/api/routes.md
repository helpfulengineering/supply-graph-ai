# Open Matching Engine API

## Introduction

The Open Matching Engine (OME) API provides programmatic access to match requirements (specified in OKH format) with capabilities (specified in OKW format) and generate valid manufacturing solutions represented as Supply Trees. This document outlines the API architecture, routes, methods, and design decisions.

## Architecture Overview

The API is structured around the three core domain models:

1. **OpenKnowHow (OKH)** - Represents hardware design specifications and requirements
2. **OpenKnowWhere (OKW)** - Represents manufacturing capabilities and facilities
3. **Supply Trees** - Represents valid solutions matching OKH requirements with OKW capabilities

Each domain has its own set of routes for creation, validation, retrieval, and specialized operations. The API follows RESTful principles with consistent response formats and appropriate status codes.

## API Versioning

All routes are prefixed with `/v1` to enable future versioning. This approach allows for introducing breaking changes in future versions without disrupting existing clients.

```
/v1/okh/...
/v1/okw/...
/v1/match/...
```

Future versions would be accessible via `/v2`, `/v3`, etc., with the previous versions maintained for backward compatibility as needed.

## Storage Integration

The OME API includes comprehensive storage integration with Azure Blob Storage:

### Azure Blob Storage Features
- **Automatic OKW Loading**: The `/v1/match` endpoint automatically loads all OKW facilities from the configured Azure container
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

### OKH Routes

#### Create

```
POST /v1/okh/create
```

Creates a new OKH manifest.

**Request:**
```json
{
  "title": "New Hardware Project",
  "license": {...},
  ...
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "New Hardware Project",
  ...
}
```

#### Read (Get)

```
GET /v1/okh/{id}
```

Retrieves an OKH object by ID.

**Query Parameters:**
- `component` (optional): Specific component to retrieve (e.g., "manufacturing_specs", "parts")

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Example Hardware Project",
  "version": "1.0.0",
  ...
}
```

#### List (Multiple Read)

```
GET /v1/okh
```

Retrieves a list of OKH objects.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Results per page (default: 20)
- `filter` (optional): Filter criteria (e.g., "title=contains:Hardware")

**Response:**
```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Example Hardware Project",
      ...
    },
    ...
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

#### Update

```
PUT /v1/okh/{id}
```

Updates an existing OKH manifest.

**Request:**
```json
{
  "title": "Updated Hardware Project",
  "license": {...},
  ...
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Updated Hardware Project",
  ...
}
```

#### Delete

```
DELETE /v1/okh/{id}
```

Deletes an OKH manifest.

**Response:**
```json
{
  "success": true,
  "message": "OKH manifest deleted successfully"
}
```

#### Validation and Normalization

```
POST /v1/okh/validate
```

Validates and normalizes an OKH object, returning a cleaned version with validation information.

**Request:**
```json
{
  "content": {...},  // OKH object or file content
  "validation_context": "manufacturing"  // Optional context
}
```

**Response:**
```json
{
  "valid": true,
  "normalized_content": {...},  // Normalized OKH object
  "issues": [  // Only present if validation issues found
    {
      "severity": "warning",
      "message": "Missing recommended field: description",
      "path": ["description"]
    }
  ],
  "completeness_score": 0.85
}
```

#### Requirements Extraction

```
POST /v1/okh/extract
```

Extracts requirements from an OKH object for matching.

**Request:**
```json
{
  "content": {...}  // OKH object or file content
}
```

**Response:**
```json
{
  "requirements": [
    {
      "process_name": "milling",
      "parameters": {"tolerance": "0.1mm"},
      ...
    },
    ...
  ]
}
```

### OKW Routes

#### Create

```
POST /v1/okw/create
```

Creates a new OKW facility.

**Request:**
```json
{
  "name": "New Manufacturing Facility",
  "location": {...},
  ...
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "New Manufacturing Facility",
  ...
}
```

#### Read (Get)

```
GET /v1/okw/{id}
```

Retrieves an OKW facility by ID.

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Manufacturing Facility",
  "location": {...},
  ...
}
```

#### List (Multiple Read)

```
GET /v1/okw
```

Retrieves a list of OKW facilities.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Results per page (default: 20)
- `filter` (optional): Filter criteria (e.g., "name=contains:Factory")

**Response:**
```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Manufacturing Facility",
      ...
    },
    ...
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

#### Update

```
PUT /v1/okw/{id}
```

Updates an existing OKW facility.

**Request:**
```json
{
  "name": "Updated Manufacturing Facility",
  "location": {...},
  ...
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Updated Manufacturing Facility",
  ...
}
```

#### Delete

```
DELETE /v1/okw/{id}
```

Deletes an OKW facility.

**Response:**
```json
{
  "success": true,
  "message": "OKW facility deleted successfully"
}
```

#### Search

```
GET /v1/okw/search
```

Searches for facilities by criteria.

**Query Parameters:**
- `location` (optional): Geographic location to search near
- `capabilities` (optional): List of required capabilities
- `materials` (optional): List of required materials
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Results per page (default: 20)

**Response:**
```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Manufacturing Facility",
      "location": {...},
      ...
    },
    ...
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

#### Validation

```
POST /v1/okw/validate
```

Validates an OKW object, returning validation information.

**Request:**
```json
{
  "content": {...}  // OKW object or file content
}
```

**Response:**
```json
{
  "valid": true,
  "normalized_content": {...},  // Normalized OKW object
  "issues": []  // Only present if validation issues found
}
```

#### Capabilities Extraction

```
POST /v1/okw/extract
```

Extracts capabilities from an OKW object for matching.

**Request:**
```json
{
  "content": {...}  // OKW object or file content
}
```

**Response:**
```json
{
  "capabilities": [
    {
      "type": "milling",
      "parameters": {"max_size": "500mm"},
      ...
    },
    ...
  ]
}
```

### Supply Tree Routes

#### Create

```
POST /v1/supply-tree/create
```

Creates a supply tree manually.

**Request:**
```json
{
  "workflows": [...],
  "connections": [...],
  ...
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "workflows": {...},
  ...
}
```

#### Read (Get)

```
GET /v1/supply-tree/{id}
```

Retrieves a specific supply tree.

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "workflows": {...},
  ...
}
```

#### List (Multiple Read)

```
GET /v1/supply-tree
```

Retrieves a list of supply trees.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Results per page (default: 20)
- `filter` (optional): Filter criteria (e.g., "confidence=gt:0.8")

**Response:**
```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "workflows": {...},
      ...
    },
    ...
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

#### Update

```
PUT /v1/supply-tree/{id}
```

Updates an existing supply tree.

**Request:**
```json
{
  "workflows": [...],
  "connections": [...],
  ...
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "workflows": {...},
  ...
}
```

#### Delete

```
DELETE /v1/supply-tree/{id}
```

Deletes a supply tree.

**Response:**
```json
{
  "success": true,
  "message": "Supply tree deleted successfully"
}
```

#### Optimization

```
POST /v1/supply-tree/{id}/optimize
```

Optimizes a supply tree based on specific criteria.

**Request:**
```json
{
  "criteria": {
    "priority": "cost",  // or "time", "quality"
    "weights": {...}
  }
}
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "workflows": {...},
  "optimization_metrics": {
    "cost": 1250.00,
    "time": "24h",
    "quality_score": 0.95
  },
  ...
}
```

#### Validation

```
POST /v1/supply-tree/{id}/validate
```

Validates a supply tree against specified requirements and capabilities.

**Request:**
```json
{
  "okh_reference": "okh-id",  // Optional OKH reference
  "okw_references": ["facility-id-1", "facility-id-2"]  // Optional OKW references
}
```

**Response:**
```json
{
  "valid": true,
  "issues": [],
  "confidence": 0.85
}
```

#### Export

```
GET /v1/supply-tree/{id}/export
```

Exports a supply tree to a specific format.

**Query Parameters:**
- `format`: Export format (e.g., "json", "xml", "graphml")

**Response:**
The supply tree in the requested format.

### Matching Routes

#### Match Requirements to Capabilities

```
POST /v1/match
```

**Enhanced matching endpoint** that matches OKH requirements with OKW capabilities to generate valid supply trees. Supports multiple input methods and advanced filtering.

**Request:**
```json
{
  // OKH Input (choose ONE of the following):
  "okh_manifest": {...},           // Inline OKH manifest object
  "okh_id": "uuid-here",          // Reference to stored OKH manifest
  "okh_url": "https://example.com/manifest.yaml",  // Remote OKH manifest URL
  
  // Optional OKW Filtering
  "okw_filters": {
    "location": {
      "country": "United States",
      "city": "San Francisco"
    },
    "access_type": "public",
    "capabilities": ["3D Printing", "CNC Milling"],
    "facility_status": "active"
  },
  
  // Optional Optimization
  "optimization_criteria": {
    "cost": 0.5,
    "quality": 0.3,
    "speed": 0.2
  }
}
```

**Response:**
```json
{
  "solutions": [
    {
      "tree": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Manufacturing Solution",
        "description": "Complete manufacturing workflow",
        "node_count": 15,
        "edge_count": 18
      },
      "score": 0.85,
      "metrics": {
        "facility_count": 3,
        "requirement_count": 8,
        "capability_count": 12
      }
    }
  ],
  "metadata": {
    "solution_count": 1,
    "facility_count": 3,
    "optimization_criteria": {
      "cost": 0.5,
      "quality": 0.3,
      "speed": 0.2
    }
  }
}
```

**Key Features:**
- **Multiple OKH Input Methods**: Accept inline manifests, storage references, or remote URLs
- **Automatic OKW Loading**: Loads all OKW facilities from Azure Blob Storage automatically
- **Advanced Filtering**: Filter facilities by location, capabilities, access type, and status
- **Real-time Processing**: Processes YAML/JSON files from storage in real-time
- **Domain-Specific Extraction**: Uses registered domain extractors for requirements and capabilities

**Enhanced Matching Workflow:**
1. **OKH Input Processing**: Validates and processes OKH manifest from one of three input methods
2. **Storage Integration**: Automatically loads all OKW facilities from Azure Blob Storage
3. **File Processing**: Parses YAML/JSON files and converts to `ManufacturingFacility` objects
4. **Filtering**: Applies optional filters to narrow down relevant facilities
5. **Domain Extraction**: Uses domain-specific extractors to extract requirements and capabilities
6. **Matching Logic**: Compares requirements against capabilities using domain-specific matching
7. **Solution Generation**: Creates supply tree solutions with confidence scoring
8. **Response Formatting**: Returns serialized solutions with metadata

#### Validate Supply Tree

```
POST /v1/match/validate
```

Validates an existing supply tree against requirements and capabilities.

**Request:**
```json
{
  "supply_tree": {...},  // Supply tree object
  "okh_reference": "okh-id",  // Optional OKH reference
  "okw_references": ["facility-id-1", "facility-id-2"]  // Optional OKW references
}
```

**Response:**
```json
{
  "valid": true,
  "issues": [],
  "confidence": 0.85
}
```

### Additional Utility Routes

#### Available Domains

```
GET /v1/domains
```

Lists available domains (manufacturing, cooking, etc.).

**Response:**
```json
{
  "domains": [
    {
      "id": "manufacturing",
      "name": "Manufacturing Domain",
      "description": "Hardware manufacturing capabilities"
    },
    {
      "id": "cooking",
      "name": "Cooking Domain",
      "description": "Food preparation capabilities"
    }
  ]
}
```

#### Validation Contexts

```
GET /v1/contexts/{domain}
```

Lists validation contexts for a specific domain.

**Response:**
```json
{
  "contexts": [
    {
      "id": "hobby",
      "name": "Hobby Manufacturing",
      "description": "Non-commercial, limited quality requirements"
    },
    {
      "id": "professional",
      "name": "Professional Manufacturing",
      "description": "Commercial-grade production"
    },
    {
      "id": "medical",
      "name": "Medical Manufacturing",
      "description": "Medical device quality standards"
    }
  ]
}
```

#### Simulation

```
POST /v1/match/simulate
```

Simulates the execution of a supply tree.

**Request:**
```json
{
  "supply_tree": {...},
  "parameters": {
    "start_time": "2023-01-01T00:00:00Z",
    "resource_availability": {...}
  }
}
```

**Response:**
```json
{
  "success": true,
  "completion_time": "2023-01-10T15:30:00Z",
  "critical_path": [...],
  "bottlenecks": [...],
  "resource_utilization": {...}
}
```

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

## Implementation Status

### ✅ Fully Implemented Routes

**Core Matching Engine:**
- `POST /v1/match` - Enhanced matching with multiple input methods and filtering
- `POST /v1/match/validate` - Supply tree validation

**OKH Management:**
- `POST /v1/okh/create` - Create OKH manifests
- `GET /v1/okh/{id}` - Retrieve OKH manifests
- `POST /v1/okh/validate` - Validate OKH manifests
- `POST /v1/okh/extract` - Extract requirements from OKH

**OKW Management:**
- `POST /v1/okw/create` - Create OKW facilities
- `GET /v1/okw/{id}` - Retrieve OKW facilities
- `GET /v1/okw/search` - Search OKW facilities
- `POST /v1/okw/validate` - Validate OKW facilities
- `POST /v1/okw/extract` - Extract capabilities from OKW

**Supply Tree Management:**
- `POST /v1/supply-tree/create` - Create supply trees
- `GET /v1/supply-tree/{id}` - Retrieve supply trees
- `POST /v1/supply-tree/{id}/validate` - Validate supply trees

**Utility Routes:**
- `GET /v1/domains` - List available domains
- `GET /v1/contexts/{domain}` - Get domain contexts

### 🚧 Partially Implemented Routes

**List Operations:**
- `GET /v1/okh` - List OKH manifests (basic implementation)
- `GET /v1/okw` - List OKW facilities (basic implementation)
- `GET /v1/supply-tree` - List supply trees (basic implementation)

### 📋 Planned Routes

**Advanced Operations:**
- `PUT /v1/okh/{id}` - Update OKH manifests
- `DELETE /v1/okh/{id}` - Delete OKH manifests
- `PUT /v1/okw/{id}` - Update OKW facilities
- `DELETE /v1/okw/{id}` - Delete OKW facilities
- `PUT /v1/supply-tree/{id}` - Update supply trees
- `DELETE /v1/supply-tree/{id}` - Delete supply trees

**Advanced Features:**
- `POST /v1/supply-tree/{id}/optimize` - Optimize supply trees
- `GET /v1/supply-tree/{id}/export` - Export supply trees
- `POST /v1/match/simulate` - Simulate supply tree execution

## API Documentation & Developer Experience

### Interactive Documentation
The OME API provides comprehensive interactive documentation:

- **Main API Docs**: `http://localhost:8001/docs` - System endpoints and overview
- **Full API Docs**: `http://localhost:8001/v1/docs` - Complete API documentation with all 19 endpoints
- **OpenAPI Schema**: `http://localhost:8001/v1/openapi.json` - Machine-readable API specification

### Developer Features
- **Request Validation**: Comprehensive input validation with detailed error messages
- **Type Safety**: Full Pydantic model validation and serialization
- **Error Handling**: Consistent error response format with helpful error messages
- **Async Support**: Full async/await support for high-performance operations
- **CORS Support**: Cross-origin resource sharing enabled for web applications

### Testing & Development
- **Health Check**: `GET /health` - System status and registered domains
- **Root Endpoint**: `GET /` - API information and navigation links
- **Hot Reload**: Development server with automatic reload on code changes

## Future Considerations

### API Extensions
- Webhook support for asynchronous processing
- WebSocket API for real-time updates
- Batch processing for large-scale operations

### Integration Support
- OAuth 2.0 authentication
- Integration with external manufacturing systems
- Export to standard manufacturing formats

### Advanced Features
- Machine learning-based matching
- Real-time facility status updates
- Distributed manufacturing network optimization