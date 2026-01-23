# Open Hardware Manager - Developer Guide


## Table of Contents

1. [Quick Start](#quick-start)
2. [System Architecture](#system-architecture)
3. [Domain Management](#domain-management)
4. [API Usage](#api-usage)
5. [Multi-Layered Matching](#multi-layered-matching)
6. [Storage Integration](#storage-integration)
7. [Development Workflow](#development-workflow)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Python 3.11+
- Conda environment manager
- Azure Blob Storage account (for OKW facilities)

### Setup

```bash
# Clone the repository
git clone git@github.com:helpfulengineering/supply-graph-ai.git
cd supply-graph-ai

# Activate or create conda environment
conda create -n ohm 
conda activate ohm

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your Azure storage credentials:
# AZURE_STORAGE_ACCOUNT=your_storage_account
# AZURE_STORAGE_KEY=your_storage_key
# AZURE_STORAGE_CONTAINER=okw

# Start the development server
python run.py
```

### Verify Installation

```bash
# Health check
curl http://localhost:8001/health

# List available OKW facilities
curl http://localhost:8001/v1/okw

# Test basic matching
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "okh_manifest": {
      "title": "Test Hardware",
      "repo": "https://github.com/example/test",
      "version": "1.0.0",
      "license": {"hardware": "CERN-OHL-S-2.0"},
      "licensor": "Test Org",
      "documentation_language": "en",
      "function": "Test hardware project",
      "manufacturing_processes": ["CNC", "3D Printing"]
    }
  }'
```

### Project Scaffolding

Generate OKH-compliant project structures with the scaffolding system:

```bash
# Generate a new project scaffold
curl -X POST "http://localhost:8001/v1/api/okh/scaffold" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "my-hardware-project",
    "template_level": "standard",
    "output_format": "json"
  }'

# Generate with filesystem output
curl -X POST "http://localhost:8001/v1/api/okh/scaffold" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "arduino-sensor",
    "template_level": "detailed",
    "output_format": "filesystem",
    "output_path": "/home/user/projects"
  }'
```

The scaffolding system generates:
- OKH-compliant directory structure
- MkDocs documentation setup
- OKH manifest template with guidance
- BOM templates and assembly guides
- Socumentation stubs

For detailed scaffolding documentation, see the [Scaffolding Guide](../scaffolding/index.md).

## System Architecture

### Core Components

1. **Matching Service**: Multi-layered matching engine with direct and heuristic matching
2. **Storage Service**: Azure Blob Storage integration for OKW facilities
3. **Domain Registry**: Extensible domain system (manufacturing, cooking)
4. **API Layer**: FastAPI-based REST API with documentation

### Data Flow

```
OKH Manifest → Matching Service → Storage Service → OKW Facilities → Supply Trees
```

### Key Services

- **MatchingService**: Core matching logic with multi-layered approach
- **StorageService**: Azure Blob Storage integration
- **OKHService**: OKH manifest management
- **OKWService**: OKW facility management
- **DomainRegistry**: Unified domain management and component registration
- **DomainDetector**: Multi-layered domain detection system

## Domain Management

The Open Hardware Manager supports multiple domains through a unified domain management system. This enables the engine to operate across different domains (manufacturing, cooking, etc.) while maintaining consistent behavior.

### Domain System Overview

The domain management system provides:

- **Multi-domain Support**: Seamless operation across different domains
- **Domain Detection**: Automatic detection of the appropriate domain from input data
- **Domain-specific Components**: Specialized extractors, matchers, and validators
- **Unified API**: Consistent interface regardless of domain
- **Health Monitoring**: Real-time monitoring of domain system health

### Supported Domains

#### Manufacturing Domain
- **Input Types**: `okh`, `okw`
- **Output Types**: `supply_tree`, `manufacturing_plan`
- **Components**: OKHExtractor, OKHMatcher, OKHValidator

#### Cooking Domain
- **Input Types**: `recipe`, `kitchen`
- **Output Types**: `cooking_workflow`, `meal_plan`
- **Components**: CookingExtractor, CookingMatcher, CookingValidator

### Domain Detection

The system uses a multi-layered approach:

1. **Explicit Detection**: Uses domain attributes when provided
2. **Type-based Detection**: Maps input types to domains
3. **Content Analysis**: Analyzes content for domain-specific keywords
4. **Fallback**: Uses single available domain when only one exists

### Domain Management API

#### List Domains
```bash
curl http://localhost:8001/v1/match/domains
```

#### Get Domain Information
```bash
curl http://localhost:8001/v1/match/domains/manufacturing
```

#### Domain Health Check
```bash
curl http://localhost:8001/v1/match/domains/manufacturing/health
```

#### Detect Domain
```bash
curl -X POST http://localhost:8001/v1/match/detect-domain \
  -H "Content-Type: application/json" \
  -d '{
    "requirements_data": {"type": "okh", "content": {"manufacturing_processes": ["CNC"]}},
    "capabilities_data": {"type": "okw", "content": {"equipment": ["CNC mill"]}}
  }'
```

### Adding New Domains

1. **Create Domain Components**:
   ```python
   from src.core.registry.domain_registry import DomainRegistry, DomainMetadata, DomainStatus
   
   # Create your domain components
   class NewDomainExtractor(BaseExtractor):
       # Implementation
   
   class NewDomainMatcher:
       # Implementation
   
   class NewDomainValidator:
       # Implementation
   ```

2. **Register Domain**:
   ```python
   metadata = DomainMetadata(
       name="new_domain",
       display_name="New Domain",
       description="Description of the new domain",
       version="1.0.0",
       status=DomainStatus.ACTIVE,
       supported_input_types={"input_type1", "input_type2"},
       supported_output_types={"output_type1", "output_type2"}
   )
   
   DomainRegistry.register_domain(
       domain_name="new_domain",
       extractor=NewDomainExtractor(),
       matcher=NewDomainMatcher(),
       validator=NewDomainValidator(),
       metadata=metadata
   )
   ```

3. **Update Configuration**:
   - Add to `src/config/domains.py`
   - Update type mappings and keywords
   - Add domain-specific documentation

### Domain Testing

Test the domain management system:

```bash
# Run simple integration test
python test_domain_management_simple.py

# Run interactive demo
python test_domain_system.py

# Run full pytest suite
pytest tests/test_domain_management_integration.py -v
```

## API Usage

### Core Endpoints

#### Matching Endpoint
```python
POST /v1/match
```

**Developer Note: Inline Capabilities Support**

The matching endpoint supports two modes for providing OKW facility capabilities:

1. **Cloud Storage Mode (Default)**: The API automatically loads OKW facilities from cloud storage. This is the production mode.

2. **Local Development Mode**: You can provide OKW facilities inline using the `okw_facilities` field. This enables local development without cloud storage setup.

**When to Use Inline Capabilities:**
- Local development and testing
- Demonstrations and prototypes  
- Offline development environments
- Custom facility data not in cloud storage
- Rapid prototyping with specific configurations

**Priority Logic:**
- If `okw_facilities` is provided → uses inline facilities (skips cloud storage)
- If `okw_facilities` is not provided → loads from cloud storage (existing behavior)
- Filters apply to both inline and cloud-loaded facilities

**Request Body (Cloud Storage Mode):**
```json
{
  "okh_manifest": {
    "title": "Hardware Project",
    "manufacturing_processes": ["CNC", "3D Printing"],
    // ... other OKH fields
  },
  "okw_filters": {
    "access_type": "Restricted",
    "facility_status": "Active"
  }
}
```

**Request Body (Local Development Mode):**
```json
{
  "okh_manifest": {
    "title": "Hardware Project",
    "manufacturing_processes": ["CNC", "3D Printing"],
    // ... other OKH fields
  },
  "okw_facilities": [
    {
      "id": "local-facility-1",
      "name": "Local Machine Shop",
      "manufacturing_processes": ["CNC", "3D Printing", "Assembly"],
      "equipment": [
        {
          "equipment_type": "https://en.wikipedia.org/wiki/CNC_mill",
          "manufacturing_process": "https://en.wikipedia.org/wiki/Machining",
          "make": "Haas",
          "model": "VF-2",
          "condition": "Excellent"
        }
      ],
      "location": {
        "city": "San Francisco",
        "country": "United States"
      },
      "access_type": "Public",
      "facility_status": "Active"
    }
  ],
  "okw_filters": {
    "access_type": "Public",
    "facility_status": "Active"
  }
}
```

**Response:**
```json
{
  "solutions": [
    {
      "tree": {
        "id": "uuid",
        "name": "Hardware Project",
        "description": "Manufacturing solution",
        "node_count": 0,
        "edge_count": 0
      },
      "score": 1.0,
      "metrics": {
        "facility_count": 1,
        "requirement_count": 3,
        "capability_count": 3
      }
    }
  ],
  "metadata": {
    "solution_count": 1,
    "facility_count": 1,
    "optimization_criteria": {}
  }
}
```

#### File Upload Matching Endpoint
```python
POST /v1/match/upload
```

**Form Data:**
- `okh_file`: Uploaded OKH file (YAML or JSON)
- `access_type`: (Optional) Filter by access type
- `facility_status`: (Optional) Filter by facility status  
- `location`: (Optional) Filter by location
- `capabilities`: (Optional) Comma-separated list of required capabilities
- `materials`: (Optional) Comma-separated list of required materials

**Example Usage:**
```bash
# Upload OKH file with filters
curl -X POST http://localhost:8001/v1/match/upload \
  -F "okh_file=@path/to/okh_manifest.json" \
  -F "access_type=Restricted" \
  -F "facility_status=Active"

# Upload OKH file without filters
curl -X POST http://localhost:8001/v1/match/upload \
  -F "okh_file=@path/to/okh_manifest.yaml" | jq .
```

**Python Example:**
```python
import httpx

async def match_from_file():
    async with httpx.AsyncClient() as client:
        with open("path/to/okh_manifest.json", "rb") as f:
            files = {"okh_file": ("okh_manifest.json", f, "application/json")}
            data = {
                "access_type": "Restricted",
                "facility_status": "Active"
            }
            response = await client.post(
                "http://localhost:8001/v1/match/upload",
                files=files,
                data=data
            )
        return response.json()
```

#### OKW Management Endpoints

**List Facilities:**
```python
GET /v1/okw
```

**Search Facilities:**
```python
GET /v1/okw/search?access_type=Restricted&facility_status=Active
```

### Python Client Examples

```python
import httpx
import asyncio

async def match_requirements():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/v1/match",
            json={
                "okh_manifest": {
                    "title": "CNC Bracket",
                    "manufacturing_processes": ["CNC", "Deburring"],
                    "license": {"hardware": "CERN-OHL-S-2.0"},
                    "licensor": "Test Org",
                    "documentation_language": "en",
                    "function": "Precision bracket"
                }
            }
        )
        return response.json()

async def search_facilities():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8001/v1/okw/search",
            params={"access_type": "Membership"}
        )
        return response.json()

# Usage
results = asyncio.run(match_requirements())
facilities = asyncio.run(search_facilities())
```

## Multi-Layered Matching

### Layer 1: Direct Matching
- Exact string comparison (case-insensitive)
- Example: "CNC" ↔ "CNC"

### Layer 2: Heuristic Matching
- Rule-based matching with synonyms and abbreviations
- Example: "CNC" ↔ "Computer Numerical Control"

### Supported Heuristic Rules

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

### Adding New Heuristic Rules

To add new heuristic rules, update the `HEURISTIC_RULES` dictionary in `src/core/services/matching_service.py`:

```python
HEURISTIC_RULES = {
    # ... existing rules ...
    "your_new_rule": ["synonym1", "synonym2", "synonym3"],
}
```

## Storage Integration

### Azure Blob Storage Configuration

**Environment Variables:**
```bash
AZURE_STORAGE_ACCOUNT=your_storage_account
AZURE_STORAGE_KEY=your_storage_key
AZURE_STORAGE_CONTAINER=okw
```

### Supported File Formats

- **YAML**: `.yaml`, `.yml` files
- **JSON**: `.json` files

### OKW File Structure

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

### Adding New OKW Facilities

1. Create a YAML or JSON file with the facility data
2. Upload to your Azure Blob Storage container
3. The system will automatically load it on the next request

## Development Workflow

### Code Organization

```
src/
├── core/
│   ├── api/           # FastAPI routes and models
│   ├── services/      # Core business logic
│   ├── models/        # Data models
│   ├── domains/       # Domain-specific implementations
│   └── storage/       # Storage providers
├── config/            # Configuration management
└── utils/             # Utility functions
```

### Adding New Features

1. **Create tests first** (TDD approach)
2. **Implement minimal changes**
3. **Test incrementally**
4. **Update documentation**

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings
- Include error handling

### Testing

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_matching_layers.py

# Run with coverage
python -m pytest --cov=src
```

## Testing

### Unit Tests

```python
import pytest
from src.core.services.matching_service import MatchingService

@pytest.mark.asyncio
async def test_direct_matching():
    service = await MatchingService.get_instance()
    result = service._direct_match("CNC", "CNC")
    assert result is True

@pytest.mark.asyncio
async def test_heuristic_matching():
    service = await MatchingService.get_instance()
    result = service._heuristic_match("CNC", "Computer Numerical Control")
    assert result is True
```

### Integration Tests

```python
import httpx
import pytest

@pytest.mark.asyncio
async def test_matching_endpoint():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/v1/match",
            json={
                "okh_manifest": {
                    "title": "Test Hardware",
                    "manufacturing_processes": ["CNC"]
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "solutions" in data
```

### API Testing

```bash
# Test health endpoint
curl http://localhost:8001/health

# Test OKW listing
curl http://localhost:8001/v1/okw

# Test matching
curl -X POST http://localhost:8001/v1/match \
  -H "Content-Type: application/json" \
  -d '{"okh_manifest": {...}}'
```

## Troubleshooting

### Common Issues

#### 1. Storage Connection Issues
**Error**: `'NoneType' object has no attribute 'list_objects'`

**Solution**: Check Azure storage configuration in `.env` file:
```bash
AZURE_STORAGE_ACCOUNT=your_account
AZURE_STORAGE_KEY=your_key
AZURE_STORAGE_CONTAINER=okw
```

#### 2. Enum Comparison Issues
**Error**: Filtering returns 0 results when it should return matches

**Solution**: This was fixed by using `.value` instead of `str()` for enum comparison:
```python
# Fixed
facility_access_type = facility.access_type.value.lower()

# Was broken
facility_access_type = str(facility.access_type).lower()
```

#### 3. Route Conflicts
**Error**: 404 errors or wrong endpoints being called

**Solution**: Ensure route order is correct - specific routes before parameterized routes:
```python
@router.get("/search")  # Specific route first
async def search_okw():
    pass

@router.get("/{id}")    # Parameterized route second
async def get_okw(id: UUID):
    pass
```

### Debugging

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Check Storage Status
```python
from src.core.services.storage_service import StorageService

async def check_storage():
    service = await StorageService.get_instance()
    print(f"Storage configured: {service.manager is not None}")
```

#### Test Matching Logic
```python
from src.core.services.matching_service import MatchingService

async def test_matching():
    service = await MatchingService.get_instance()
    await service.initialize()
    
    # Test direct matching
    result = service._direct_match("CNC", "CNC")
    print(f"Direct match: {result}")
    
    # Test heuristic matching
    result = service._heuristic_match("CNC", "Computer Numerical Control")
    print(f"Heuristic match: {result}")
```

### Performance Optimization

#### Caching
- OKW facilities are loaded from storage on each request
- TODO: caching for production use

#### Async Operations
- All I/O operations are async
- Use `httpx.AsyncClient` for API calls
- Use `asyncio.run()` for testing

#### Error Handling
- All endpoints include error handling
- Check logs for detailed error information
- Use appropriate HTTP status codes