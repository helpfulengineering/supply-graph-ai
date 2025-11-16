# API Route Placeholders Implementation Specification

## Overview

This specification defines the implementation plan for completing placeholder API route implementations. These are critical endpoints that currently return empty data, 404 errors, or placeholder responses, but have the underlying infrastructure available to implement them properly.

## Current State Analysis

### Issue 1: OKW Extract Endpoint Placeholder

**Location**: `src/core/api/routes/okw.py:775`

**Current Implementation:**
```python
@router.post("/extract", response_model=OKWExtractResponse)
async def extract_capabilities(request: OKWExtractRequest):
    """Extract capabilities from an OKW object"""
    # Placeholder implementation
    return OKWExtractResponse(
        capabilities=[]  # Return empty list for now
    )
```

**Problems:**
- Returns empty capabilities list
- Doesn't use existing extraction infrastructure
- OKHExtractor has `extract_capabilities()` method available
- Missing error handling and validation

**Context:**
- `OKWExtractRequest` contains `content: Dict[str, Any]` (OKW facility data)
- `OKWExtractResponse` expects `capabilities: List[Capability]`
- `OKHExtractor.extract_capabilities()` method exists and returns `ExtractionResult[NormalizedCapabilities]`
- Used in matching service (see `matching_service.py:175`)

**Severity**: Critical - Incomplete feature

### Issue 2: Utility Endpoints Placeholders

**Location**: `src/core/api/routes/utility.py:75,173`

**Current Implementation:**

**Domains Endpoint (line 75):**
```python
async def list_domains(...):
    # Placeholder implementation
    domains = [
        Domain(id="manufacturing", name="Manufacturing Domain", ...),
        Domain(id="cooking", name="Cooking Domain", ...)
    ]
```

**Contexts Endpoint (line 173):**
```python
async def list_contexts(...):
    # Placeholder implementation
    if domain == "manufacturing":
        contexts = [
            Context(id="hobby", name="Hobby Manufacturing", ...),
            Context(id="professional", name="Professional Manufacturing", ...)
        ]
```

**Problems:**
- Hardcoded domain/context lists
- Doesn't use `DomainRegistry` which has actual domain metadata
- Missing dynamic context detection
- No filtering or pagination support

**Context:**
- `DomainRegistry` has `get_all_metadata()` method
- `DomainRegistry` has `list_domains()` method
- Domain metadata includes all needed information
- Contexts should be derived from validation framework quality levels

**Severity**: High - Incomplete features

### Issue 3: Supply Tree CRUD Placeholders

**Location**: `src/core/api/routes/supply_tree.py:223,288,358,414,464`

**Current Implementation:**

**GET /{id} (line 223):**
```python
async def get_supply_tree(id: UUID, ...):
    # Placeholder implementation - return 404 for now
    raise HTTPException(status_code=404, detail=f"Supply tree with ID {id} not found")
```

**GET / (line 288):**
```python
async def list_supply_trees(...):
    # Placeholder implementation - return empty list
    results = []
    total_items = 0
```

**PUT /{id} (line 358):**
```python
async def update_supply_tree(id: UUID, ...):
    # Placeholder implementation - return 404 for now
    raise HTTPException(status_code=404, detail=f"Supply tree with ID {id} not found")
```

**DELETE /{id} (line 414):**
```python
async def delete_supply_tree(id: UUID, ...):
    # Placeholder implementation
    return create_success_response(message=f"Supply tree with ID {id} deleted successfully", ...)
```

**POST /{id}/validate (line 464):**
```python
async def validate_supply_tree(...):
    # Placeholder implementation
    return ValidationResult(valid=True, confidence=0.8, issues=[])
```

**Problems:**
- All operations return placeholders despite storage service existing
- `StorageService` has `save_supply_tree()`, `load_supply_tree()`, `list_supply_trees()` methods
- Missing actual CRUD operations
- No error handling for storage operations

**Context:**
- `StorageService.save_supply_tree(tree)` - saves supply tree
- `StorageService.load_supply_tree(tree_id)` - loads supply tree by ID
- `StorageService.list_supply_trees(limit, offset)` - lists supply trees
- Storage service is already integrated and working
- Supply tree validation should use validation framework

**Severity**: Critical - Core CRUD operations incomplete

### Issue 4: Match Validation Endpoint

**Location**: `src/core/api/routes/match.py:321`

**Current Implementation:**
```python
# TODO: Implement validation using matching service and new validation framework
# For now, return a placeholder response
return ValidationResult(is_valid=True, score=0.8, ...)
```

**Note**: This is already covered in the Core Functionality TODOs specification. Reference that spec for implementation details.

## Requirements

### Functional Requirements

1. **OKW Extract Endpoint**
   - Extract capabilities from OKW facility data
   - Use `OKHExtractor.extract_capabilities()` method
   - Convert `NormalizedCapabilities` to `List[Capability]`
   - Handle extraction errors gracefully
   - Return proper error responses

2. **Utility Endpoints**
   - List domains from `DomainRegistry`
   - List contexts based on validation framework quality levels
   - Support filtering and pagination
   - Return proper domain metadata

3. **Supply Tree CRUD**
   - GET: Load supply tree from storage
   - LIST: List supply trees with pagination
   - PUT: Update supply tree in storage
   - DELETE: Delete supply tree from storage
   - VALIDATE: Validate supply tree using validation framework

### Non-Functional Requirements

1. **Error Handling**
   - Proper HTTP status codes
   - Meaningful error messages
   - Consistent error response format

2. **Performance**
   - Efficient storage operations
   - Proper pagination
   - Caching where appropriate

3. **Consistency**
   - Use existing service methods
   - Follow established patterns
   - Consistent response formats

## Design Decisions

### OKW Extract Strategy

**Use OKHExtractor:**
- Leverage existing extraction infrastructure
- Consistent with matching service usage
- Proper normalization and validation

**Capability Conversion:**
- Convert `NormalizedCapabilities` to `List[Capability]`
- Extract from `content.capabilities` field
- Handle empty results gracefully

### Utility Endpoints Strategy

**Use DomainRegistry:**
- Single source of truth for domains
- Dynamic domain discovery
- Proper metadata access

**Context Derivation:**
- Use validation framework quality levels
- Map to domain-specific contexts
- Support filtering by domain

### Supply Tree CRUD Strategy

**Use StorageService:**
- Existing storage methods
- Consistent storage patterns
- Proper error handling

**Validation Integration:**
- Use validation framework for supply tree validation
- Support quality levels and strict mode
- Return detailed validation results

## Implementation Specification

### 1. Implement OKW Extract Endpoint

**File: `src/core/api/routes/okw.py`**

**Update `extract_capabilities` method:**

```python
@router.post("/extract", response_model=OKWExtractResponse)
@track_performance("okw_extract_capabilities")
async def extract_capabilities(
    request: OKWExtractRequest,
    okw_service: OKWService = Depends(get_okw_service),
    http_request: Request = None
):
    """
    Extract capabilities from an OKW object.
    
    This endpoint extracts manufacturing capabilities from OKW facility data
    using the domain-specific extractor. The extracted capabilities can be
    used for matching against OKH requirements.
    
    Args:
        request: OKW extract request containing facility data
        okw_service: OKW service dependency
        http_request: HTTP request object
        
    Returns:
        OKWExtractResponse with extracted capabilities
        
    Raises:
        HTTPException: If extraction fails or data is invalid
    """
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    start_time = datetime.now()
    
    try:
        # Get domain extractor from registry
        from ...registry.domain_registry import DomainRegistry
        
        # Determine domain (default to manufacturing for OKW)
        domain = "manufacturing"
        
        # Get extractor for domain
        extractor = DomainRegistry.get_extractor(domain)
        
        # Extract capabilities using extractor
        extraction_result = extractor.extract_capabilities(request.content)
        
        # Check if extraction was successful
        if not extraction_result.data:
            logger.warning(
                f"Extraction returned no data for OKW content",
                extra={"request_id": request_id}
            )
            return OKWExtractResponse(capabilities=[])
        
        # Extract capabilities from normalized data
        normalized_capabilities = extraction_result.data
        capabilities_list = []
        
        # Convert NormalizedCapabilities to List[Capability]
        # The content field contains the capabilities
        if hasattr(normalized_capabilities, 'content'):
            content = normalized_capabilities.content
            
            # Extract capabilities array
            if isinstance(content, dict):
                capabilities_data = content.get('capabilities', [])
                
                # Convert to Capability objects
                from ...models.base.base_types import Capability
                
                for cap_data in capabilities_data:
                    if isinstance(cap_data, dict):
                        capability = Capability(
                            name=cap_data.get('process_name', cap_data.get('name', '')),
                            type=cap_data.get('type', 'process'),
                            parameters=cap_data.get('parameters', {}),
                            limitations=cap_data.get('limitations', {})
                        )
                        capabilities_list.append(capability)
                    elif isinstance(cap_data, Capability):
                        # Already a Capability object
                        capabilities_list.append(cap_data)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(
            f"Extracted {len(capabilities_list)} capabilities from OKW content",
            extra={
                "request_id": request_id,
                "capability_count": len(capabilities_list),
                "processing_time": processing_time
            }
        )
        
        return OKWExtractResponse(capabilities=capabilities_list)
        
    except ValueError as e:
        # Invalid domain or extractor not found
        error_response = create_error_response(
            error=f"Invalid domain or extractor not available: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
            request_id=request_id,
            suggestion="Please check the domain configuration"
        )
        logger.error(
            f"Extraction failed: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.model_dump(mode='json')
        )
        
    except Exception as e:
        # Generic error handling
        error_response = create_error_response(
            error=f"Failed to extract capabilities: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please check the OKW content format and try again"
        )
        logger.error(
            f"Extraction error: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )
```

### 2. Implement Utility Endpoints

**File: `src/core/api/routes/utility.py`**

**Update `list_domains` method:**

```python
async def list_domains(
    filter_params: DomainFilterRequest = Depends(),
    http_request: Request = None
):
    """Enhanced domain listing with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    start_time = datetime.now()
    
    try:
        # Get domains from DomainRegistry
        from ...registry.domain_registry import DomainRegistry
        
        # Get all domain metadata
        all_metadata = DomainRegistry.get_all_metadata(include_disabled=False)
        
        # Convert to Domain objects
        domains = []
        for domain_name, metadata in all_metadata.items():
            domain = Domain(
                id=metadata.name,
                name=metadata.display_name,
                description=metadata.description,
                status=metadata.status.value,
                version=metadata.version,
                supported_input_types=list(metadata.supported_input_types),
                supported_output_types=list(metadata.supported_output_types),
                documentation_url=metadata.documentation_url,
                maintainer=metadata.maintainer
            )
            domains.append(domain)
        
        # Apply name filter if provided
        if filter_params.name:
            domains = [
                d for d in domains 
                if filter_params.name.lower() in d.name.lower() or 
                   filter_params.name.lower() in d.id.lower()
            ]
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create enhanced response
        response_data = {
            "domains": [domain.model_dump(mode='json') for domain in domains],
            "processing_time": processing_time,
            "total_domains": len(domains)
        }
        
        return create_success_response(
            message="Domains listed successfully",
            data=response_data,
            request_id=request_id
        )
        
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error listing domains: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )
```

**Update `list_contexts` method:**

```python
async def list_contexts(
    domain: str = Path(..., description="Domain name"),
    filter_params: ContextFilterRequest = Depends(),
    http_request: Request = None
):
    """Enhanced context listing with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    start_time = datetime.now()
    
    try:
        # Validate domain exists
        from ...registry.domain_registry import DomainRegistry
        
        try:
            domain_metadata = DomainRegistry.get_domain_metadata(domain)
        except ValueError:
            error_response = create_error_response(
                error=f"Domain '{domain}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion=f"Available domains: {', '.join(DomainRegistry.list_domains())}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode='json')
            )
        
        # Get contexts based on validation framework quality levels
        # Quality levels map to contexts
        quality_levels = ["hobby", "professional", "medical"]
        
        contexts = []
        for level in quality_levels:
            # Map quality level to context
            context_id = level
            context_name = level.title() + " " + domain_metadata.display_name.split()[0]
            context_description = f"{level.title()} level validation and matching"
            
            context = Context(
                id=context_id,
                name=context_name,
                description=context_description,
                domain=domain,
                quality_level=level
            )
            contexts.append(context)
        
        # Apply name filter if provided
        if filter_params.name:
            contexts = [
                c for c in contexts 
                if filter_params.name.lower() in c.name.lower() or 
                   filter_params.name.lower() in c.id.lower()
            ]
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create enhanced response
        response_data = {
            "contexts": [context.model_dump(mode='json') for context in contexts],
            "processing_time": processing_time,
            "total_contexts": len(contexts),
            "domain": domain
        }
        
        return create_success_response(
            message="Contexts listed successfully",
            data=response_data,
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error listing contexts: {str(e)}",
            extra={"request_id": request_id, "domain": domain, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )
```

### 3. Implement Supply Tree CRUD Operations

**File: `src/core/api/routes/supply_tree.py`**

**Update `get_supply_tree` method:**

```python
async def get_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    http_request: Request = None,
    storage_service: StorageService = Depends()
):
    """Enhanced supply tree retrieval with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Load supply tree from storage
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available"
            )
        
        supply_tree = await storage_service.load_supply_tree(id)
        
        if not supply_tree:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode='json')
            )
        
        # Convert to response format
        response_data = {
            "id": str(supply_tree.id),
            "facility_name": supply_tree.facility_name,
            "okh_reference": supply_tree.okh_reference,
            "confidence_score": supply_tree.confidence_score,
            "estimated_cost": supply_tree.estimated_cost,
            "estimated_time": supply_tree.estimated_time,
            "materials_required": supply_tree.materials_required,
            "capabilities_used": supply_tree.capabilities_used,
            "match_type": supply_tree.match_type,
            "metadata": supply_tree.metadata,
            "creation_time": supply_tree.creation_time.isoformat()
        }
        
        return create_success_response(
            message="Supply tree retrieved successfully",
            data=response_data,
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error getting supply tree {id}: {str(e)}",
            extra={"request_id": request_id, "supply_tree_id": str(id), "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )
```

**Update `list_supply_trees` method:**

```python
async def list_supply_trees(
    pagination: PaginationParams = Depends(),
    filter: Optional[str] = Query(None, description="Filter criteria"),
    http_request: Request = None,
    storage_service: StorageService = Depends()
):
    """Enhanced supply tree listing with pagination and metrics."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available"
            )
        
        # List supply trees from storage
        supply_tree_list = await storage_service.list_supply_trees(
            limit=pagination.page_size,
            offset=(pagination.page - 1) * pagination.page_size
        )
        
        # Convert to response format
        results = []
        for tree_info in supply_tree_list:
            # tree_info is a dict with metadata
            # Load full tree if needed, or use metadata
            if isinstance(tree_info, dict):
                results.append({
                    "id": tree_info.get("id"),
                    "facility_name": tree_info.get("facility_name"),
                    "okh_reference": tree_info.get("okh_reference"),
                    "confidence_score": tree_info.get("confidence_score"),
                    "match_type": tree_info.get("match_type"),
                    "creation_time": tree_info.get("created_at")
                })
        
        # Get total count (may need separate method or estimate)
        total_items = len(results)  # This is approximate, may need total count method
        
        # Create pagination info
        total_pages = (total_items + pagination.page_size - 1) // pagination.page_size if total_items > 0 else 0
        
        return create_success_response(
            message="Supply trees listed successfully",
            data={
                "items": results,
                "pagination": {
                    "page": pagination.page,
                    "page_size": pagination.page_size,
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "has_next": pagination.page < total_pages,
                    "has_previous": pagination.page > 1
                }
            },
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error listing supply trees: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )
```

**Update `update_supply_tree` method:**

```python
async def update_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    request: SupplyTreeCreateRequest = None,
    http_request: Request = None,
    storage_service: StorageService = Depends()
):
    """Enhanced supply tree update with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available"
            )
        
        # Load existing supply tree
        existing_tree = await storage_service.load_supply_tree(id)
        
        if not existing_tree:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode='json')
            )
        
        # Update fields from request
        if request.facility_id:
            # Load facility and update
            from ...services.okw_service import OKWService, get_okw_service
            okw_service = await get_okw_service()
            facility = await okw_service.get(request.facility_id)
            if facility:
                existing_tree.facility_name = facility.name
        
        if request.okh_reference:
            existing_tree.okh_reference = request.okh_reference
        
        if request.confidence_score is not None:
            existing_tree.confidence_score = request.confidence_score
        
        if request.estimated_cost is not None:
            existing_tree.estimated_cost = request.estimated_cost
        
        if request.estimated_time:
            existing_tree.estimated_time = request.estimated_time
        
        if request.materials_required:
            existing_tree.materials_required = request.materials_required
        
        if request.capabilities_used:
            existing_tree.capabilities_used = request.capabilities_used
        
        if request.match_type:
            existing_tree.match_type = request.match_type
        
        if request.metadata:
            existing_tree.metadata.update(request.metadata)
        
        # Save updated tree
        await storage_service.save_supply_tree(existing_tree)
        
        # Convert to response format
        response_data = {
            "id": str(existing_tree.id),
            "facility_name": existing_tree.facility_name,
            "okh_reference": existing_tree.okh_reference,
            "confidence_score": existing_tree.confidence_score,
            "estimated_cost": existing_tree.estimated_cost,
            "estimated_time": existing_tree.estimated_time,
            "materials_required": existing_tree.materials_required,
            "capabilities_used": existing_tree.capabilities_used,
            "match_type": existing_tree.match_type,
            "metadata": existing_tree.metadata,
            "creation_time": existing_tree.creation_time.isoformat()
        }
        
        return create_success_response(
            message="Supply tree updated successfully",
            data=response_data,
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error updating supply tree {id}: {str(e)}",
            extra={"request_id": request_id, "supply_tree_id": str(id), "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )
```

**Update `delete_supply_tree` method:**

```python
async def delete_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    http_request: Request = None,
    storage_service: StorageService = Depends()
):
    """Enhanced supply tree deletion with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available"
            )
        
        # Check if supply tree exists
        existing_tree = await storage_service.load_supply_tree(id)
        
        if not existing_tree:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode='json')
            )
        
        # Delete from storage
        # Note: StorageService may need a delete_supply_tree method
        # For now, we'll need to check if it exists or implement it
        if hasattr(storage_service, 'delete_supply_tree'):
            await storage_service.delete_supply_tree(id)
        else:
            # Fallback: use storage manager directly
            key = f"supply-trees/{id}.json"
            await storage_service.manager.delete_object(key)
        
        logger.info(
            f"Deleted supply tree {id}",
            extra={"request_id": request_id, "supply_tree_id": str(id)}
        )
        
        return create_success_response(
            message=f"Supply tree with ID {id} deleted successfully",
            data={},
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error deleting supply tree {id}: {str(e)}",
            extra={"request_id": request_id, "supply_tree_id": str(id), "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )
```

**Update `validate_supply_tree` method:**

```python
async def validate_supply_tree(
    request: SupplyTreeValidateRequest,
    id: UUID = Path(..., title="The ID of the supply tree"),
    http_request: Request = None,
    storage_service: StorageService = Depends()
):
    """Enhanced supply tree validation with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available"
            )
        
        # Load supply tree
        supply_tree = await storage_service.load_supply_tree(id)
        
        if not supply_tree:
            error_response = create_error_response(
                error=f"Supply tree with ID {id} not found",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the supply tree ID and try again"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode='json')
            )
        
        # Use validation framework
        # Reference: See Core Functionality TODOs spec for validation implementation
        # For now, use placeholder but structure for real validation
        
        from ...validation.engine import ValidationEngine
        from ...validation.context import ValidationContext
        
        validation_engine = ValidationEngine()
        context = ValidationContext()
        context.add_data("supply_tree", supply_tree)
        context.add_data("quality_level", request.quality_level or "professional")
        context.add_data("strict_mode", request.strict_mode or False)
        
        # Validate supply tree
        validation_result = await validation_engine.validate(
            data=supply_tree,
            validation_type="supply_tree",
            context=context
        )
        
        # Convert to response format
        return ValidationResult(
            valid=validation_result.valid,
            confidence=validation_result.confidence if hasattr(validation_result, 'confidence') else 0.8,
            issues=[
                {
                    "type": "error" if error.severity == "error" else "warning",
                    "message": error.message,
                    "field": error.field if hasattr(error, 'field') else None
                }
                for error in validation_result.errors
            ] + [
                {
                    "type": "warning",
                    "message": warning.message,
                    "field": warning.field if hasattr(warning, 'field') else None
                }
                for warning in validation_result.warnings
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error validating supply tree {id}: {str(e)}",
            extra={"request_id": request_id, "supply_tree_id": str(id), "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )
```

## Integration Points

### 1. OKW Extract

- Uses `DomainRegistry` to get extractor
- Uses `OKHExtractor.extract_capabilities()` method
- Converts `NormalizedCapabilities` to `List[Capability]`

### 2. Utility Endpoints

- Uses `DomainRegistry.get_all_metadata()` for domains
- Uses validation framework quality levels for contexts
- Supports filtering and pagination

### 3. Supply Tree CRUD

- Uses `StorageService` methods for all operations
- Integrates with validation framework for validation
- Follows existing response patterns

## Testing Considerations

### Unit Tests

1. **OKW Extract Tests:**
   - Test successful extraction
   - Test empty content
   - Test invalid domain
   - Test extraction errors

2. **Utility Endpoints Tests:**
   - Test domain listing
   - Test context listing
   - Test filtering
   - Test pagination

3. **Supply Tree CRUD Tests:**
   - Test GET with existing tree
   - Test GET with non-existent tree
   - Test LIST with pagination
   - Test UPDATE
   - Test DELETE
   - Test VALIDATE

### Integration Tests

1. **End-to-End OKW Extract:**
   - Test full extraction workflow
   - Test with real OKW data

2. **End-to-End Supply Tree CRUD:**
   - Test create, read, update, delete cycle
   - Test validation integration

## Migration Plan

### Phase 1: Implementation (Current)
- Implement OKW extract endpoint
- Implement utility endpoints
- Implement supply tree CRUD operations

### Phase 2: Enhancement (Future)
- Add filtering to supply tree list
- Add search capabilities
- Add bulk operations

## Success Criteria

1. ✅ OKW extract endpoint returns actual capabilities
2. ✅ Utility endpoints return real domain/context data
3. ✅ Supply tree CRUD operations work with storage
4. ✅ All placeholders replaced with real implementations
5. ✅ Proper error handling in all endpoints
6. ✅ Tests pass

## Open Questions / Future Enhancements

1. **StorageService.delete_supply_tree:**
   - Should we add this method to StorageService?
   - Or use storage manager directly?

2. **Supply Tree List Total Count:**
   - How to get accurate total count for pagination?
   - May need separate count method

3. **Context Derivation:**
   - Should contexts be configurable?
   - Or always derived from quality levels?

## Dependencies

### Existing Dependencies

- `DomainRegistry` - Domain management
- `StorageService` - Storage operations
- `OKHExtractor` - Capability extraction
- `ValidationEngine` - Validation framework

### No New Dependencies

- Uses only existing infrastructure

## Implementation Order

1. Implement OKW extract endpoint
2. Implement utility endpoints
3. Implement supply tree GET endpoint
4. Implement supply tree LIST endpoint
5. Implement supply tree UPDATE endpoint
6. Implement supply tree DELETE endpoint
7. Implement supply tree VALIDATE endpoint
8. Write tests
9. Update documentation

