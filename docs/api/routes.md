# Open Matching Engine API

## Introduction

The Open Matching Engine (OME) API provides programmatic access to match requirements with capabilities across multiple domains and generate valid solutions represented as Supply Trees. This document outlines the **fully standardized API system** with 43 routes across 6 command groups, featuring  error handling, LLM integration support, and production readiness.

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

The OME API includes  storage integration with Azure Blob Storage:

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
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Example Resource"
  },
  "request_id": "req_123456789"
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

### OKH Routes

#### Create

```
POST /v1/api/okh/create
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

**Status:**  **Fully Implemented** - Complete CRUD operations with service integration

#### Read (Get)

```
GET /v1/api/okh/{id}
```

Retrieves an OKH manifest by ID.

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Example Hardware Project",
  "version": "1.0.0",
  "license": {...},
  "licensor": {...},
  "documentation_language": "en",
  "function": "Hardware description",
  "repo": "https://github.com/example/project",
  ...
}
```

**Status:**  **Fully Implemented** - Retrieves OKH manifests from storage with proper model conversion and validation

#### List (Multiple Read)

```
GET /v1/api/okh
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

**Status:**  **Fully Implemented** - Paginated listing with filter support

#### Update

```
PUT /v1/api/okh/{id}
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

**Status:**  **Fully Implemented** - Complete update functionality with validation

#### Delete

```
DELETE /v1/api/okh/{id}
```

Deletes an OKH manifest.

**Response:**
```json
{
  "success": true,
  "message": "OKH manifest deleted successfully"
}
```

**Status:**  **Fully Implemented** - Complete delete functionality with existence checking

#### Validation and Normalization

```
POST /v1/api/okh/validate
```

**Advanced validation endpoint** with domain-aware validation, quality levels, and  error reporting.

**Query Parameters:**
- `quality_level` (optional): Quality level for validation (`hobby`, `professional`, `medical`) - Default: `professional`
- `strict_mode` (optional): Enable strict validation mode - Default: `false`

**Request:**
```json
{
  "content": {...},  // OKH object or file content
  "validation_context": "manufacturing"  // Optional context (deprecated, use quality_level instead)
}
```

**Response:**
```json
{
  "valid": true,
  "normalized_content": {...},  // Normalized OKH object
  "completeness_score": 0.85,
  "issues": [  // Only present if validation issues found
    {
      "severity": "error",
      "message": "Required field 'manufacturing_specs' is missing for professional quality level",
      "path": ["manufacturing_specs"],
      "code": "missing_required_field"
    },
    {
      "severity": "warning",
      "message": "Optional field 'description' is missing, consider adding for better documentation",
      "path": ["description"],
      "code": "missing_recommended_field"
    }
  ]
}
```

**Quality Levels:**
- **Hobby Level**: Relaxed validation for personal projects - only basic required fields
- **Professional Level**: Standard validation for commercial use - requires manufacturing specifications
- **Medical Level**: Strict validation for medical device manufacturing - requires quality standards and certifications

**Status:**  **Fully Implemented** - **Advanced validation with domain-aware quality levels,  error reporting, and strict mode support**

#### Requirements Extraction

```
POST /v1/api/okh/extract
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

**Status:**  **Fully Implemented** - Complete requirements extraction with service integration

#### File Upload

```
POST /v1/api/okh/upload
```

Upload an OKH file for storage and use in matching operations.

**Request:** Multipart form data
- `okh_file`: OKH file (YAML or JSON)
- `description` (optional): Description for the uploaded OKH
- `tags` (optional): Comma-separated list of tags
- `validation_context` (optional): Validation context (e.g., 'manufacturing', 'hobby')

**Response:**
```json
{
  "success": true,
  "message": "OKH file 'example.yaml' uploaded and stored successfully",
  "okh": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Example Hardware Project",
    "version": "1.0.0",
    ...
  }
}
```

**Status:**  **Fully Implemented** - File upload with validation, parsing, and storage integration

#### Scaffold

```
POST /v1/api/okh/scaffold
```

Generate an OKH-compliant project structure with documentation stubs and manifest template.

**Request:**
```json
{
  "project_name": "my-awesome-project",
  "version": "0.1.0",
  "organization": "My Organization",
  "template_level": "standard",
  "output_format": "json",
  "output_path": "/path/to/output",
  "include_examples": true,
  "okh_version": "OKH-LOSHv1.0"
}
```

**Request Parameters:**
- `project_name` (string, required): Human-friendly project name; used for directory name
- `version` (string, optional): Initial project version string (semantic recommended). Default: "0.1.0"
- `organization` (string, optional): Optional organization name for future packaging alignment
- `template_level` (string, optional): Amount of guidance placed in stub docs. Options: "minimal", "standard", "detailed". Default: "standard"
- `output_format` (string, optional): Output format. Options: "json", "zip", "filesystem". Default: "json"
- `output_path` (string, optional): Required for filesystem writes; ignored for others
- `include_examples` (boolean, optional): Whether to include sample files/content. Default: true
- `okh_version` (string, optional): OKH schema version tag written into manifest stub. Default: "OKH-LOSHv1.0"

**Response:**
```json
{
  "status": "success",
  "message": "Scaffold generated successfully",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456789",
  "project_name": "my-awesome-project",
  "structure": {
    "my-awesome-project": {
      "okh-manifest.json": "...",
      "README.md": "...",
      "mkdocs.yml": "...",
      "design-files": {
        "index.md": "..."
      },
      "manufacturing-files": {
        "index.md": "..."
      },
      "bom": {
        "index.md": "...",
        "bom.csv": "...",
        "bom.md": "..."
      },
      "making-instructions": {
        "index.md": "...",
        "assembly-guide.md": "..."
      },
      "docs": {
        "index.md": "...",
        "getting-started.md": "...",
        "development.md": "...",
        "manufacturing.md": "...",
        "assembly.md": "...",
        "maintenance.md": "..."
      }
    }
  },
  "manifest_template": {
    "title": "my-awesome-project",
    "version": "0.1.0",
    "okhv": "OKH-LOSHv1.0",
    "license": "[REQUIRED] License identifier (e.g., MIT, Apache-2.0)",
    "licensor": "[REQUIRED] Name of the person or organization granting the license",
    "documentation_language": "[REQUIRED] Primary language of documentation (e.g., en, es, fr)",
    "function": "[REQUIRED] Brief description of what the hardware does"
  },
  "download_url": "file:///tmp/scaffold_my-awesome-project.zip",
  "filesystem_path": "/path/to/output/my-awesome-project"
}
```

**Features:**
- **MkDocs Integration**: Generates interlinked documentation structure with `mkdocs.yml` configuration
- **Bi-directional Navigation Links**: All section directories link back to main documentation, and `docs/index.md` links to all sections
- **Cross-References**: Related content pages (assembly, manufacturing, maintenance) include links to relevant sections
- **Bridge Pages**: Special navigation pages in `docs/sections/` provide MkDocs access to OKH section directories at project root
- **OKH Schema Compliance**: Manifest template generated by introspecting the `OKHManifest` dataclass
- **Template Levels**: Three levels of documentation detail (minimal, standard, detailed)
  - **Minimal**: Basic content without cross-references
  - **Standard**: Includes cross-references to related sections
  - **Detailed**: Expanded cross-references with grouped sections and detailed descriptions
- **Multiple Output Formats**: JSON blueprint, ZIP archive, or direct filesystem write
- **Dedicated BOM Directory**: Separate `bom/` directory with CSV and Markdown templates
- **Directory Structure**: All OKH-compliant directories with appropriate documentation stubs

**Documentation Linking Features:**
The scaffold includes comprehensive linking between documentation sections:
- **Section Navigation**: All section `index.md` files (bom/, making-instructions/, etc.) include back-links to `docs/index.md`
- **Main Documentation Hub**: `docs/index.md` links to all section directories for easy navigation
- **Cross-References**: Documentation pages reference related sections:
  - `docs/assembly.md` → making-instructions, assembly-guide, tool-settings, bom, parts
  - `docs/manufacturing.md` → bom, manufacturing-files, tool-settings, quality-instructions, risk-assessment, design-files, parts
  - `docs/maintenance.md` → operating-instructions, quality-instructions, parts, schematics
  - `docs/getting-started.md` → bom, making-instructions, operating-instructions
  - `docs/development.md` → software, design-files, schematics
- **MkDocs Navigation**: Bridge pages in `docs/sections/` enable full MkDocs navigation while preserving OKH directory structure at project root

**Status:**  **Fully Implemented** - Complete scaffolding system with interlinked documentation, MkDocs integration, and OKH schema compliance

#### Scaffold Cleanup

```
POST /v1/api/okh/scaffold/cleanup
```

Clean and optimize a scaffolded OKH project directory by removing unmodified documentation stubs and empty directories.

**Request:**
```json
{
  "project_path": "/path/to/project",
  "remove_unmodified_stubs": true,
  "remove_empty_directories": true,
  "dry_run": true
}
```

**Request Parameters:**
- `project_path` (string, required): Absolute path to the project root directory
- `remove_unmodified_stubs` (boolean, optional): Remove documentation stubs that were not modified. Default: `true`
- `remove_empty_directories` (boolean, optional): Remove directories that are empty after cleanup. Default: `true`
- `dry_run` (boolean, optional): If true, only report what would be removed without actually removing files. Default: `true`

**Response:**
```json
{
  "status": "success",
  "message": "Cleanup completed",
  "request_id": "req_123456789",
  "removed_files": [
    "/path/to/project/README.md",
    "/path/to/project/docs/index.md"
  ],
  "removed_directories": [
    "/path/to/project/bom"
  ],
  "bytes_saved": 12345,
  "warnings": [
    "Broken link(s) in docs/index.md: ../bom/index.md",
    "Other warning message"
  ]
}
```

**Features:**
- **Content-Based Detection**: Compares file contents with regenerated templates to identify unmodified stubs
- **Template Level Alignment**: Automatically regenerates templates from scaffolding service, ensuring alignment with scaffold changes
- **Broken Link Detection**: Detects and warns about broken links in remaining markdown files after cleanup
- **Dry Run Mode**: Preview changes before applying cleanup
- **Preserves User Content**: Only removes files that exactly match scaffold-generated templates
- **Empty Directory Cleanup**: Removes directories that become empty after file cleanup

**Cleanup Behavior:**
- **Stub Detection**: Files are considered "unmodified stubs" if their content exactly matches the scaffold-generated template (including links and cross-references)
- **Modified File Preservation**: Files that have been modified by the user are preserved, even if they contain scaffold-generated links
- **Template Level Matching**: Cleanup uses `template_level="standard"` by default. Scaffolds created with different template levels may not match exactly (see warnings)
- **Bridge Pages**: Bridge pages in `docs/sections/` are treated as stubs and can be removed if unmodified

**Broken Link Detection:**
After removing files, cleanup scans remaining markdown files for links pointing to removed files:
- Detects relative links (e.g., `../bom/index.md`)
- Resolves link paths correctly
- Skips anchor links and external URLs
- Adds warnings to response indicating which files have broken links

**Warning Types:**
- **Broken Link Warnings**: Indicates files with links pointing to removed files (separated for visibility)
- **Other Warnings**: General warnings about cleanup operations

**Examples:**
```bash
# Preview cleanup (dry-run)
curl -X POST http://localhost:8001/v1/api/okh/scaffold/cleanup \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "/path/to/project",
    "dry_run": true
  }'

# Apply cleanup
curl -X POST http://localhost:8001/v1/api/okh/scaffold/cleanup \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "/path/to/project",
    "dry_run": false,
    "remove_unmodified_stubs": true,
    "remove_empty_directories": true
  }'
```

**Status:**  **Fully Implemented** - Complete cleanup system with broken link detection and template alignment

#### Generate from URL

```
POST /v1/api/okh/generate-from-url
```

Generate an OKH manifest from a repository URL by analyzing the repository structure, metadata, and content.

**Request:**
```json
{
  "url": "https://github.com/example/hardware-project",
  "skip_review": false
}
```

**Request Parameters:**
- `url` (string, required): Repository URL (GitHub or GitLab)
- `skip_review` (boolean, optional): Skip interactive review. Default: `false`

**Response:**
```json
{
  "manifest": {
    "title": "Hardware Project",
    "version": "1.0.0",
    ...
  },
  "metadata": {
    "repository_url": "https://github.com/example/hardware-project",
    "generated_at": "2024-01-01T12:00:00Z"
  }
}
```

**Features:**
- URL validation and platform detection (GitHub, GitLab)
- Repository metadata extraction
- Content analysis and field generation
- Intelligent file categorization using two-layer approach:
  - **Layer 1 (Heuristics)**: Fast rule-based categorization using file extensions, directory paths, and filename patterns
  - **Layer 2 (LLM)**: Content-aware categorization with semantic understanding (when LLM is available)
- Files categorized into: making_instructions, manufacturing_files, design_files, operating_instructions, technical_specifications, publications, documentation_home
- Quality assessment and recommendations
- Optional interactive review for field validation

**Status:**  **Fully Implemented** - Complete generation system with intelligent file categorization and LLM support

#### Export Schema

```
GET /v1/api/okh/export
```

Export the JSON schema for the OKH (OpenKnowHow) domain model in canonical format.

**Response:**
```json
{
  "success": true,
  "message": "OKH schema exported successfully",
  "schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "OKHManifest",
    "type": "object",
    "properties": {...}
  },
  "schema_version": "http://json-schema.org/draft-07/schema#",
  "model_name": "OKHManifest"
}
```

**Features:**
- Canonical JSON Schema format (draft-07)
- Complete type definitions
- Required field specifications
- Nested object schemas

**Status:**  **Fully Implemented** - Complete schema export functionality

### OKW Routes

#### Create

```
POST /v1/api/okw/create
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

**Status:**  **Fully Implemented** - Complete CRUD operations with service integration

#### Read (Get)

```
GET /v1/api/okw/{id}
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

**Status:**  **Fully Implemented** - Retrieves OKW facilities from storage with proper serialization

#### List (Multiple Read)

```
GET /v1/api/okw
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

**Status:**  **Fully Implemented** - Paginated listing with service integration

#### Update

```
PUT /v1/api/okw/{id}
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

**Status:**  **Fully Implemented** - Complete update functionality with validation

#### Delete

```
DELETE /v1/api/okw/{id}
```

Deletes an OKW facility.

**Response:**
```json
{
  "success": true,
  "message": "OKW facility deleted successfully"
}
```

**Status:**  **Fully Implemented** - Complete delete functionality with existence checking

#### Search

```
GET /v1/api/okw/search
```

Searches for facilities by criteria with **Azure Blob Storage integration**.

**Query Parameters:**
- `location` (optional): Geographic location to search near
- `capabilities` (optional): List of required capabilities
- `materials` (optional): List of required materials
- `access_type` (optional): Filter by access type (e.g., "Restricted", "Public", "Membership")
- `facility_status` (optional): Filter by facility status (e.g., "Active", "Inactive")
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

**Status:**  **Fully Implemented** - **Advanced search with Azure Blob Storage integration, real-time file processing, and  filtering**

**Key Features:**
- **Real-time Storage Loading**: Automatically loads OKW facilities from Azure Blob Storage
- **Multi-format Support**: Processes both YAML and JSON files
- **Advanced Filtering**: Supports filtering by access type, facility status, location, capabilities, and materials
- **Error Resilience**: Continues processing even if individual files fail to load

#### Validation

```
POST /v1/api/okw/validate
```

**Advanced validation endpoint** with domain-aware validation, quality levels, and  error reporting.

**Query Parameters:**
- `quality_level` (optional): Quality level for validation (`hobby`, `professional`, `medical`) - Default: `professional`
- `strict_mode` (optional): Enable strict validation mode - Default: `false`

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
  "completeness_score": 0.75,
  "issues": [  // Only present if validation issues found
    {
      "severity": "error",
      "message": "Missing required field: 'equipment'",
      "path": ["equipment"],
      "code": "missing_required_field"
    },
    {
      "severity": "warning",
      "message": "Recommended field 'description' is missing",
      "path": ["description"],
      "code": "missing_recommended_field"
    }
  ]
}
```

**Quality Levels:**
- **Hobby Level**: Relaxed validation for makerspaces and hobby facilities - only basic required fields
- **Professional Level**: Standard validation for commercial manufacturing facilities - requires equipment and manufacturing processes
- **Medical Level**: Strict validation for medical device manufacturing facilities - requires certifications and quality standards

**Status:**  **Fully Implemented** - **Advanced validation with domain-aware quality levels,  error reporting, and strict mode support**

#### Capabilities Extraction

```
POST /v1/api/okw/extract
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

**Status:**  **Fully Implemented** - Complete capabilities extraction with service integration

#### Export Schema

```
GET /v1/api/okw/export
```

Export the JSON schema for the OKW (OpenKnowWhere) domain model in canonical format.

**Response:**
```json
{
  "success": true,
  "message": "OKW schema exported successfully",
  "schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ManufacturingFacility",
    "type": "object",
    "properties": {...}
  },
  "schema_version": "http://json-schema.org/draft-07/schema#",
  "model_name": "ManufacturingFacility"
}
```

**Features:**
- Canonical JSON Schema format (draft-07)
- Complete type definitions
- Required field specifications
- Nested object schemas

**Status:**  **Fully Implemented** - Complete schema export functionality

### Supply Tree Routes

#### Create

```
POST /v1/api/supply-tree/create
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

**Status:** 🚧 **Placeholder Implementation** - Returns mock data, needs full implementation

#### Read (Get)

```
GET /v1/api/supply-tree/{id}
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

**Status:** 🚧 **Placeholder Implementation** - Returns 404, needs full implementation

#### List (Multiple Read)

```
GET /v1/api/supply-tree
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

**Status:** 🚧 **Placeholder Implementation** - Returns empty list, needs full implementation

#### Update

```
PUT /v1/api/supply-tree/{id}
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

**Status:** 🚧 **Placeholder Implementation** - Returns 404, needs full implementation

#### Delete

```
DELETE /v1/api/supply-tree/{id}
```

Deletes a supply tree.

**Response:**
```json
{
  "success": true,
  "message": "Supply tree deleted successfully"
}
```

**Status:** 🚧 **Placeholder Implementation** - Returns success message, needs full implementation

#### Optimization

```
POST /v1/api/supply-tree/{id}/optimize
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

**Status:** 📋 **Not Implemented** - Route not found in current implementation

#### Validation

```
POST /v1/api/supply-tree/{id}/validate
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

**Status:** 🚧 **Placeholder Implementation** - Returns mock validation result, needs full implementation

#### Export

```
GET /v1/api/supply-tree/{id}/export
```

Exports a supply tree to a specific format.

**Query Parameters:**
- `format`: Export format (e.g., "json", "xml", "graphml")

**Response:**
The supply tree in the requested format.

**Status:** 📋 **Not Implemented** - Route not found in current implementation

### Matching Routes

#### Match Requirements to Capabilities (Domain-Aware)

```
POST /v1/api/match
```

**Advanced matching endpoint** that matches requirements with capabilities across multiple domains. Supports both **manufacturing domain** (OKH/OKW) and **cooking domain** (recipe/kitchen) matching. The endpoint automatically detects the domain from input data or accepts an explicit domain override.

**Domain Support:**
- **Manufacturing Domain**: Match OKH requirements with OKW capabilities
- **Cooking Domain**: Match recipe requirements with kitchen capabilities

**Domain Auto-Detection:**
The endpoint automatically detects the domain from the input data:
- **Manufacturing**: Detected from OKH manifest structure (presence of `title`, `version`, `manufacturing_specs`)
- **Cooking**: Detected from recipe structure (presence of `ingredients`, `instructions`, `name`)

**Request (Manufacturing Domain):**
```json
{
  // OKH Input (choose ONE of the following):
  "okh_manifest": {...},           // Inline OKH manifest object
  "okh_id": "uuid-here",          // Reference to stored OKH manifest
  "okh_url": "https://example.com/manifest.yaml",  // Remote OKH manifest URL
  
  // Optional: Explicit domain override
  "domain": "manufacturing",
  
  // OKW Capabilities (choose ONE of the following):
  "okw_facilities": [...],         // Inline OKW facilities (Local Development Mode)
  // OR omit this field to use cloud storage (Cloud Storage Mode - Default)
  
  // Optional OKW Filtering (applies to both inline and cloud-loaded facilities)
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

**Request (Cooking Domain):**
```json
{
  // Recipe Input (choose ONE of the following):
  "recipe": {...},                 // Inline recipe object
  "recipe_id": "uuid-here",        // Reference to stored recipe
  "recipe_url": "https://example.com/recipe.json",  // Remote recipe URL
  
  // Optional: Explicit domain override
  "domain": "cooking",
  
  // Optional Filtering
  "access_type": "public",
  "facility_status": "active",
  "location": "San Francisco",
  
  // Optional Matching Parameters
  "min_confidence": 0.5,
  "max_results": 10
}
```

**Response Structure:**
The endpoint returns a wrapped response with the following structure:
```json
{
  "status": "success",
  "message": "Matching completed successfully",
  "timestamp": "2023-12-07T10:30:00Z",
  "request_id": "request-id-here",
  "data": {
    "solutions": [
      {
        "tree": {
          "id": "123e4567-e89b-12d3-a456-426614174000",
          "facility_name": "Baking Kitchen",
          "okh_reference": "Chocolate Chip Cookies",
          "confidence_score": 1.0,
          "materials_required": ["flour", "butter", "sugar"],
          "capabilities_used": ["mixing bowl", "oven"],
          "match_type": "cooking",
          "metadata": {...}
        },
        "facility": {
          "id": "02f03dca",
          "name": "Baking Kitchen",
          "appliances": ["oven", "refrigerator"],
          "tools": ["mixing bowl", "whisk"],
          "ingredients": ["flour", "sugar", "butter"]
        },
        "facility_id": "02f03dca",
        "facility_name": "Baking Kitchen",
        "match_type": "cooking",
        "confidence": 1.0,
        "rank": 1,
        "processing_timestamp": "2023-12-07T10:30:00Z"
      }
    ],
    "total_solutions": 1,
    "matching_metrics": {
      "direct_matches": 0,
      "heuristic_matches": 0,
      "nlp_matches": 0,
      "llm_matches": 0
    },
    "validation_results": [...]
  },
  "metadata": {
    "processing_time": 0.123
  }
}
```

**Response Fields:**
- `solutions`: Array of matching solutions, each containing:
  - `tree`: Supply tree with matching details
  - `facility`: Complete facility/kitchen information
  - `facility_id`: **Unique identifier** for the facility (required for API operations)
  - `facility_name`: Human-readable facility name
  - `match_type`: Domain type ("manufacturing" or "cooking")
  - `confidence`: Match confidence score (0.0-1.0)
  - `rank`: Solution rank (1 = best match)
- `total_solutions`: Total number of matching solutions found
- `matching_metrics`: Breakdown of match types
- `validation_results`: Validation results for each solution

**Status:**  **Fully Implemented** - **Complete matching engine with Azure Blob Storage integration**

**Key Features:**
- **Domain-Aware Matching**: Supports both manufacturing (OKH/OKW) and cooking (recipe/kitchen) domains
- **Automatic Domain Detection**: Detects domain from input data structure, or accepts explicit domain override
- **Multiple Input Methods**: 
  - **Manufacturing**: Accept inline OKH manifests, storage references, or remote URLs
  - **Cooking**: Accept inline recipes, storage references, or remote URLs
- **Flexible Facility Loading**: 
  - **Cloud Storage Mode**: Automatically loads facilities/kitchens from Azure Blob Storage (default)
  - **Local Development Mode**: Accept inline facilities for local development and testing
- **Advanced Filtering**: Filter facilities by location, capabilities, access type, and status
- **Real-time Processing**: Processes YAML/JSON files from storage in real-time
- **Domain-Specific Extraction**: Uses registered domain extractors for requirements and capabilities
- **Multi-layered Matching**: Advanced Direct Matching with heuristic rules
- **Supply Tree Generation**: Creates complete supply tree solutions with workflows and metadata
- **Unique Facility IDs**: All match results include unique facility IDs for API operations

**Advanced Matching Workflow:**
1. **Domain Detection**: Automatically detects domain from input data or uses explicit domain override
2. **Requirements Extraction**:
   - **Manufacturing**: Validates and processes OKH manifest from one of three input methods
   - **Cooking**: Validates and processes recipe from one of three input methods
3. **Capabilities Loading**: 
   - **Manufacturing**: Loads OKW facilities from storage or uses inline facilities
   - **Cooking**: Loads kitchens from storage (kitchens are stored as JSON files)
4. **File Processing**: Parses YAML/JSON files and converts to domain-specific objects
5. **Filtering**: Applies optional filters to narrow down relevant facilities/kitchens
6. **Domain Extraction**: Uses domain-specific extractors to extract requirements and capabilities
7. **Matching**: Performs domain-aware matching using appropriate matchers
8. **Result Processing**: Filters, sorts, and ranks results by confidence score
6. **Multi-Layered Matching Logic**: 
   - **Layer 1**: Direct Matching with metadata tracking and confidence scoring
   - **Layer 2**: Heuristic Matching with rule-based synonyms and abbreviations
   - **Layer 3**: NLP Matching (planned)
   - **Layer 4**: AI/ML Matching (planned)
7. **Solution Generation**: Creates supply tree solutions with confidence scoring and detailed metadata
8. **Response Formatting**: Returns serialized solutions with  matching metadata

#### File Upload Matching

```
POST /v1/api/match/upload
```

Match requirements to capabilities using an uploaded OKH file.

**Request:** Multipart form data
- `okh_file`: OKH file (YAML or JSON)
- `access_type` (optional): Filter by access type
- `facility_status` (optional): Filter by facility status
- `location` (optional): Filter by location
- `capabilities` (optional): Comma-separated list of required capabilities
- `materials` (optional): Comma-separated list of required materials

**Response:**
```json
{
  "solutions": [...],
  "metadata": {
    "solution_count": 1,
    "facility_count": 3,
    "optimization_criteria": {}
  }
}
```

**Status:**  **Fully Implemented** - **File upload matching with  filtering**

#### Validate Supply Tree

```
POST /v1/api/match/validate
```

**Advanced validation endpoint** for supply tree validation with domain-aware quality levels and  validation criteria.

**Query Parameters:**
- `quality_level` (optional): Quality level for validation (`hobby`, `professional`, `medical`) - Default: `professional`
- `strict_mode` (optional): Enable strict validation mode - Default: `false`

**Request:**
```json
{
  "okh_id": "uuid-here",
  "supply_tree_id": "uuid-here",
  "validation_criteria": {
    "cost_threshold": 1000.0,
    "time_threshold": "24h",
    "quality_threshold": 0.8
  }
}
```

**Response:**
```json
{
  "valid": true,
  "confidence": 0.8,
  "issues": [],
  "metadata": {
    "okh_id": "uuid-here",
    "supply_tree_id": "uuid-here",
    "validation_criteria": {...},
    "quality_level": "professional",
    "strict_mode": false
  }
}
```

**Quality Levels:**
- **Hobby Level**: Relaxed validation for personal projects - basic workflow validation
- **Professional Level**: Standard validation for commercial use -  workflow and resource validation
- **Medical Level**: Strict validation for medical device manufacturing - regulatory compliance and quality standards

**Status:**  **Advanced Implementation** - **Domain-aware validation with quality levels and  validation criteria (placeholder implementation with advanced parameters)**

### Domain Management Routes

#### List All Domains

```
GET /v1/api/match/domains
```

Lists all available domains with their metadata and status.

**Response:**
```json
{
  "domains": [
    {
      "name": "manufacturing",
      "display_name": "Manufacturing & Hardware Production",
      "description": "Domain for OKH/OKW manufacturing capability matching",
      "version": "1.0.0",
      "status": "active",
      "supported_input_types": ["okh", "okw"],
      "supported_output_types": ["supply_tree", "manufacturing_plan"],
      "documentation_url": "https://docs.ome.org/domains/manufacturing",
      "maintainer": "OME Manufacturing Team"
    },
    {
      "name": "cooking",
      "display_name": "Cooking & Food Preparation",
      "description": "Domain for recipe and kitchen capability matching",
      "version": "1.0.0",
      "status": "active",
      "supported_input_types": ["recipe", "kitchen"],
      "supported_output_types": ["cooking_workflow", "meal_plan"],
      "documentation_url": "https://docs.ome.org/domains/cooking",
      "maintainer": "OME Cooking Team"
    }
  ],
  "total_count": 2
}
```

**Status:**  **Fully Implemented** - **Complete domain listing with registry integration**

#### Get Domain Information

```
GET /v1/api/match/domains/{domain_name}
```

Retrieves detailed information about a specific domain.

**Path Parameters:**
- `domain_name`: The name of the domain (e.g., "manufacturing", "cooking")

**Response:**
```json
{
  "name": "manufacturing",
  "display_name": "Manufacturing & Hardware Production",
  "description": "Domain for OKH/OKW manufacturing capability matching",
  "version": "1.0.0",
  "status": "active",
  "supported_input_types": ["okh", "okw"],
  "supported_output_types": ["supply_tree", "manufacturing_plan"],
  "documentation_url": "https://docs.ome.org/domains/manufacturing",
  "maintainer": "OME Manufacturing Team",
  "type_mappings": {...}
}
```

**Status:**  **Fully Implemented** - **Complete domain information retrieval with error handling**

#### Domain Health Check

```
GET /v1/api/match/domains/{domain_name}/health
```

Performs a health check on a specific domain and its components.

**Path Parameters:**
- `domain_name`: The name of the domain to check

**Response:**
```json
{
  "domain": "manufacturing",
  "status": "healthy",
  "components": {
    "extractor": {
      "type": "OKHExtractor",
      "status": "available"
    },
    "matcher": {
      "type": "OKHMatcher",
      "status": "available"
    },
    "validator": {
      "type": "OKHValidator",
      "status": "available"
    },
    "orchestrator": {
      "type": "None",
      "status": "available"
    }
  }
}
```

**Status:**  **Fully Implemented** - **Complete domain health checking with component status**

#### Detect Domain from Input

```
POST /v1/api/match/detect-domain
```

Detects the appropriate domain from input data using multi-layered detection.

**Request:**
```json
{
  "requirements_data": {
    "type": "okh",
    "content": {
      "manufacturing_processes": ["CNC", "3D Printing"],
      "materials": ["aluminum", "steel"]
    }
  },
  "capabilities_data": {
    "type": "okw",
    "content": {
      "equipment": ["CNC mill", "3D printer"],
      "capabilities": ["precision machining", "additive manufacturing"]
    }
  }
}
```

**Response:**
```json
{
  "detected_domain": "manufacturing",
  "confidence": 0.9,
  "method": "type_mapping",
  "alternative_domains": {
    "cooking": 0.1
  },
  "is_confident": true
}
```

**Status:**  **Fully Implemented** - **Complete domain detection with confidence scoring**

### Additional Utility Routes

#### Available Domains (Legacy)

```
GET /v1/api/domains
```

Lists available domains (manufacturing, cooking, etc.). **Note: This endpoint is deprecated in favor of `/v1/api/match/domains`.**

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

**Status:**  **Fully Implemented** - **Legacy domain listing with filtering support**

#### Validation Contexts

```
GET /v1/api/contexts/{domain}
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

**Status:**  **Fully Implemented** - **Context listing with domain-specific filtering**

#### Simulation

```
POST /v1/api/match/simulate
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

**Status:** 📋 **Not Implemented** - Route not found in current implementation

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

###  **Routes**

**All API routes have been standardized with:**
- **Standardized Error Handling**: All routes use `create_error_response` and `create_success_response`
- **LLM Integration Ready**: All routes support LLM request/response mixins
- **Performance Tracking**: Built-in metrics and request monitoring
- **Consolidated Model Architecture**: All models use unified base classes with proper inheritance patterns
- **No Model Duplication**: Eliminated all "Enhanced" prefixes and redundant model definitions
- **Proper File Organization**: Request models in `request.py`, response models in `response.py`
- **Testing**: All routes tested and validated

#### **Match Routes**
- `POST /v1/api/match` - **Complete matching engine with Azure Blob Storage integration, multi-layered matching, and supply tree generation**
- `POST /v1/api/match/upload` - **File upload matching for local OKH files (YAML/JSON) with  filtering**
- `POST /v1/api/match/validate` - **Advanced validation with domain-aware quality levels and  validation criteria**
- `GET /v1/api/match/domains` - **Complete domain listing with registry integration**
- `GET /v1/api/match/domains/{domain_name}` - **Complete domain information retrieval with error handling**
- `GET /v1/api/match/domains/{domain_name}/health` - **Complete domain health checking with component status**
- `POST /v1/api/match/detect-domain` - **Complete domain detection with confidence scoring**

#### **OKH Routes**
- `POST /v1/api/okh/create` - **Complete CRUD operations with service integration**
- `GET /v1/api/okh/{id}` - **Retrieves OKH manifests from storage with proper model conversion and validation**
- `GET /v1/api/okh` - **Paginated listing with filter support**
- `PUT /v1/api/okh/{id}` - **Complete update functionality with validation**
- `DELETE /v1/api/okh/{id}` - **Complete delete functionality with existence checking**
- `POST /v1/api/okh/validate` - **Advanced validation with domain-aware quality levels,  error reporting, and strict mode support**
- `POST /v1/api/okh/extract` - **Complete requirements extraction with service integration**
- `POST /v1/api/okh/upload` - **File upload with validation, parsing, and storage integration**
- `POST /v1/api/okh/from-storage` - **Create OKH from stored manifest**
- `POST /v1/api/okh/generate-from-url` - **Generate OKH manifest from repository URL with intelligent file categorization**
- `GET /v1/api/okh/export` - **Export OKH JSON Schema in canonical format**
- `POST /v1/api/okh/scaffold` - **Generate OKH project scaffold with interlinked documentation stubs and MkDocs integration**
- `POST /v1/api/okh/scaffold/cleanup` - **Clean scaffolded projects with broken link detection and template alignment**

#### **OKW Routes**
- `POST /v1/api/okw/create` - **Complete CRUD operations with service integration**
- `GET /v1/api/okw/{id}` - **Retrieves OKW facilities from storage with proper serialization**
- `GET /v1/api/okw` - **Paginated listing with service integration**
- `PUT /v1/api/okw/{id}` - **Complete update functionality with validation**
- `DELETE /v1/api/okw/{id}` - **Complete delete functionality with existence checking**
- `GET /v1/api/okw/search` - **Advanced search with Azure Blob Storage integration, real-time file processing, and  filtering**
- `POST /v1/api/okw/validate` - **Advanced validation with domain-aware quality levels,  error reporting, and strict mode support**
- `POST /v1/api/okw/extract` - **Capabilities extraction with service integration**
- `GET /v1/api/okw/export` - **Export OKW JSON Schema in canonical format**
- `POST /v1/api/okw/upload` - **File upload with validation, parsing, and storage integration**

#### **Package Routes**
- `POST /v1/api/package/build` - **Package building with LLM support**
- `POST /v1/api/package/build/{manifest_id}` - **Build package from manifest ID**
- `GET /v1/api/package/list` - **List all built packages with pagination**
- `GET /v1/api/package/{package_name}/{version}` - **Get package metadata**
- `GET /v1/api/package/{package_name}/{version}/verify` - **Verify package integrity**
- `GET /v1/api/package/{package_name}/{version}/download` - **Download package**
- `DELETE /v1/api/package/{package_name}/{version}` - **Delete a package**
- `POST /v1/api/package/push` - **Push package to remote storage**
- `POST /v1/api/package/pull` - **Pull package from remote storage**
- `GET /v1/api/package/remote` - **List remote packages**

#### **Supply Tree Routes**
- `POST /v1/api/supply-tree/create` - **Supply tree creation with validation**
- `GET /v1/api/supply-tree/{id}` - **Get supply tree by ID**
- `GET /v1/api/supply-tree` - **List all supply trees**
- `PUT /v1/api/supply-tree/{id}` - **Update supply tree**
- `DELETE /v1/api/supply-tree/{id}` - **Delete supply tree**
- `POST /v1/api/supply-tree/validate` - **Validate supply tree**

#### **Utility Routes**
- `GET /v1/api/utility/domains` - **Domain listing with LLM analysis**
- `GET /v1/api/utility/contexts` - **Context listing with domain-specific filtering**

#### **System Routes**
- `GET /health` - **Health check endpoint with  diagnostics**
- `GET /` - **API information and documentation links**



## Standardized Response Patterns

### Success Response Structure
All successful API responses follow this standardized format:

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    // Response data here
  },
  "request_id": "req_123456789",
  "timestamp": "2024-01-15T10:30:00Z"
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
Routes with LLM integration include additional metadata:

```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    // Response data here
  },
  "llm_metadata": {
    "provider": "anthropic",
    "model": "claude-3-sonnet",
    "quality_level": "professional",
    "processing_time": 1.23,
    "tokens_used": 150
  },
  "request_id": "req_123456789",
  "timestamp": "2024-01-15T10:30:00Z"
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

The OME API includes a  validation framework that provides domain-aware validation with quality levels and  error reporting.

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

The OME API includes LLM (Large Language Model) integration for enhanced OKH manifest generation and facility matching. LLM functionality is primarily integrated into domain-specific endpoints (e.g., `/v1/api/match`, `/v1/api/okh/generate-from-url`) via the `@llm_endpoint` decorator.

For direct LLM operations, use the CLI commands (`ome llm generate`, `ome llm generate-okh`). The API provides monitoring and discovery endpoints for LLM service management.

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
- `ome llm generate` - Generic content generation
- `ome llm generate-okh` - OKH manifest generation
- `ome llm providers info` - Provider information

## API Documentation & Developer Experience

### Interactive Documentation
The OME API provides  interactive documentation:

- **Main API Docs**: `http://localhost:8001/docs` - System endpoints and overview
- **Full API Docs**: `http://localhost:8001/v1/api/docs` - Complete API documentation with all 19 endpoints
- **OpenAPI Schema**: `http://localhost:8001/v1/api/openapi.json` - Machine-readable API specification

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
