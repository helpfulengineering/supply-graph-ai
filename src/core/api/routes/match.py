"""
Consolidated match API routes with standardized patterns.

This module combines the functionality from both match.py and match_enhanced.py
into a single, standardized API route file with enhanced error handling,
request validation, and response formatting.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request, status
from uuid import UUID
from typing import Optional, List
import json
import yaml
from datetime import datetime

# Import new standardized components
from ..models.base import (
    BaseAPIRequest, 
    SuccessResponse, 
    PaginationParams,
    PaginatedResponse,
    LLMRequestMixin,
    LLMResponseMixin,
    RequirementsInput,
    CapabilitiesInput,
    ValidationResult
)
from ..decorators import (
    api_endpoint,
    validate_request,
    track_performance,
    llm_endpoint,
    paginated_response
)
from ..error_handlers import create_error_response, create_success_response

# Import existing models and services
from ..models.match.request import MatchRequest, ValidateMatchRequest
from ..models.match.response import MatchResponse
from ...services.matching_service import MatchingService
from ...services.storage_service import StorageService
from ...services.okh_service import OKHService
from ...services.okw_service import OKWService
from ...models.okw import ManufacturingFacility
from ...services.domain_service import DomainDetector
from ...registry.domain_registry import DomainRegistry
from ...models.okh import OKHManifest
from ...utils.logging import get_logger

# Create consolidated router
router = APIRouter(
    tags=["match"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)

logger = get_logger(__name__)


# Enhanced request models
class EnhancedMatchRequest(BaseAPIRequest, LLMRequestMixin):
    """Enhanced match request with standardized fields and LLM support."""
    
    # Core matching fields
    okh_manifest: Optional[dict] = None
    okh_id: Optional[UUID] = None
    okh_url: Optional[str] = None
    
    # Enhanced filtering options
    access_type: Optional[str] = None
    facility_status: Optional[str] = None
    location: Optional[str] = None
    capabilities: Optional[List[str]] = None
    materials: Optional[List[str]] = None
    
    # Quality and validation options
    min_confidence: Optional[float] = 0.7
    max_results: Optional[int] = 10
    
    class Config:
        json_schema_extra = {
            "example": {
                "okh_manifest": {
                    "title": "Test OKH Manifest",
                    "version": "1.0.0",
                    "manufacturing_specs": {
                        "process_requirements": [
                            {"process_name": "PCB Assembly", "parameters": {}}
                        ]
                    }
                },
                "access_type": "public",
                "facility_status": "active",
                "min_confidence": 0.8,
                "max_results": 5,
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-3-sonnet",
                "quality_level": "professional",
                "strict_mode": False
            }
        }


class EnhancedMatchResponse(SuccessResponse, LLMResponseMixin):
    """Enhanced match response with standardized fields and LLM information."""
    
    # Core response data
    solutions: List[dict] = []
    total_solutions: int = 0
    processing_time: float = 0.0
    
    # Enhanced metadata
    matching_metrics: Optional[dict] = None
    validation_results: Optional[List[ValidationResult]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Matching completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "solutions": [
                    {
                        "facility_id": "facility_123",
                        "confidence": 0.95,
                        "matching_processes": ["PCB Assembly"],
                        "estimated_cost": 150.00
                    }
                ],
                "total_solutions": 1,
                "processing_time": 1.25,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.012,
                "matching_metrics": {
                    "direct_matches": 1,
                    "heuristic_matches": 0,
                    "nlp_matches": 0
                },
                "data": {},
                "metadata": {}
            }
        }


# Service dependencies
async def get_matching_service() -> MatchingService:
    """Get matching service instance."""
    return await MatchingService.get_instance()


async def get_storage_service() -> StorageService:
    """Get storage service instance."""
    return await StorageService.get_instance()


async def get_okh_service() -> OKHService:
    """Get OKH service instance."""
    return await OKHService.get_instance()


# Main matching endpoint (enhanced version)
@router.post(
    "",
    response_model=EnhancedMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Enhanced Requirements Matching",
    description="""
    Enhanced endpoint for matching OKH requirements with OKW capabilities.
    
    This endpoint provides:
    - Standardized request/response formats
    - LLM integration support
    - Enhanced error handling
    - Performance metrics
    - Comprehensive validation
    
    **Features:**
    - Support for multiple input formats (manifest, ID, URL)
    - Advanced filtering options
    - LLM-powered matching capabilities
    - Real-time performance tracking
    - Detailed validation results
    """
)
@api_endpoint(
    success_message="Matching completed successfully",
    include_metrics=True,
    track_llm=True
)
@validate_request(EnhancedMatchRequest)
@track_performance("enhanced_matching")
@llm_endpoint(
    default_provider="anthropic",
    default_model="claude-3-sonnet",
    track_costs=True
)
async def match_requirements_to_capabilities(
    request: EnhancedMatchRequest,
    http_request: Request,
    matching_service: MatchingService = Depends(get_matching_service),
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Enhanced matching endpoint with standardized patterns.
    
    Args:
        request: Enhanced match request with standardized fields
        http_request: HTTP request object for tracking
        matching_service: Matching service dependency
        storage_service: Storage service dependency
        okh_service: OKH service dependency
        
    Returns:
        Enhanced match response with comprehensive data
    """
    request_id = getattr(http_request.state, 'request_id', None)
    start_time = datetime.utcnow()
    
    try:
        # 1. Validate and extract OKH manifest
        okh_manifest = await _extract_okh_manifest(
            request, okh_service, storage_service, request_id
        )
        
        if not okh_manifest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide either okh_manifest, okh_id, or okh_url"
            )
        
        # 2. Get available facilities with filtering
        facilities = await _get_filtered_facilities(
            storage_service, request, request_id
        )
        
        if not facilities:
            logger.warning(
                f"No facilities found matching criteria",
                extra={
                    "request_id": request_id,
                    "filters": {
                        "access_type": request.access_type,
                        "facility_status": request.facility_status,
                        "location": request.location
                    }
                }
            )
        
        # 3. Perform matching with enhanced options
        matching_results = await _perform_enhanced_matching(
            matching_service, okh_manifest, facilities, request, request_id
        )
        
        # 4. Process and format results
        solutions = await _process_matching_results(
            matching_results, request, request_id
        )
        
        # 5. Calculate processing metrics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 6. Create enhanced response
        response_data = {
            "solutions": solutions,
            "total_solutions": len(solutions),
            "processing_time": processing_time,
            "matching_metrics": {
                "direct_matches": len([s for s in solutions if s.get("match_type") == "direct"]),
                "heuristic_matches": len([s for s in solutions if s.get("match_type") == "heuristic"]),
                "nlp_matches": len([s for s in solutions if s.get("match_type") == "nlp"]),
                "llm_matches": len([s for s in solutions if s.get("match_type") == "llm"])
            },
            "validation_results": await _validate_results(solutions, request_id)
        }
        
        logger.info(
            f"Enhanced matching completed: {len(solutions)} solutions found",
            extra={
                "request_id": request_id,
                "solutions_count": len(solutions),
                "processing_time": processing_time,
                "llm_used": request.use_llm
            }
        )
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error in enhanced matching: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump()
        )


# Validation endpoint (enhanced version)
@router.post(
    "/validate", 
    response_model=ValidationResult,
    summary="Validate Supply Tree",
    description="""
    Validate a supply tree with domain-aware validation
    
    Validates a supply tree against domain-specific validation rules
    based on the specified quality level. The validation framework provides:
    
    - **Hobby Level**: Relaxed validation for personal projects
    - **Professional Level**: Standard validation for commercial use  
    - **Medical Level**: Strict validation for medical device manufacturing
    
    Returns detailed validation results including errors, warnings, and
    completeness scoring for the supply tree workflow.
    """
)
@api_endpoint(
    success_message="Validation completed successfully",
    include_metrics=True
)
@track_performance("supply_tree_validation")
async def validate_match(
    request: ValidateMatchRequest,
    quality_level: Optional[str] = Query("professional", description="Quality level: hobby, professional, or medical"),
    strict_mode: Optional[bool] = Query(False, description="Enable strict validation mode"),
    matching_service: MatchingService = Depends(get_matching_service),
    http_request: Request = None
):
    """Enhanced validation endpoint with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        logger.info(
            "Validating supply tree",
            extra={
                "okh_id": str(request.okh_id),
                "supply_tree_id": str(request.supply_tree_id),
                "quality_level": quality_level,
                "strict_mode": strict_mode,
                "request_id": request_id
            }
        )
        
        # TODO: Implement validation using matching service and new validation framework
        # For now, return a placeholder response
        logger.debug("Using placeholder validation response")
        return ValidationResult(
            is_valid=True,
            score=0.8,
            errors=[],
            warnings=[],
            suggestions=[],
            metadata={
                "okh_id": str(request.okh_id),
                "supply_tree_id": str(request.supply_tree_id),
                "validation_criteria": request.validation_criteria,
                "quality_level": quality_level,
                "strict_mode": strict_mode
            }
        )
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            "Error validating match",
            extra={
                "okh_id": str(request.okh_id),
                "supply_tree_id": str(request.supply_tree_id),
                "error": str(e),
                "request_id": request_id
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump()
        )


# File upload endpoint (enhanced version)
@router.post(
    "/upload", 
    response_model=EnhancedMatchResponse,
    summary="Match from File Upload",
    description="""
    Match requirements to capabilities using an uploaded OKH file.
    
    This endpoint accepts a file upload (YAML or JSON) containing an OKH manifest
    and returns matching supply trees based on the requirements in the file.
    
    **Features:**
    - Support for YAML and JSON file formats
    - Advanced filtering options
    - Enhanced error handling
    - Performance metrics
    """
)
@api_endpoint(
    success_message="File upload matching completed successfully",
    include_metrics=True
)
@track_performance("file_upload_matching")
async def match_requirements_from_file(
    okh_file: UploadFile = File(..., description="OKH file (YAML or JSON)"),
    access_type: Optional[str] = Form(None, description="Filter by access type"),
    facility_status: Optional[str] = Form(None, description="Filter by facility status"),
    location: Optional[str] = Form(None, description="Filter by location"),
    capabilities: Optional[str] = Form(None, description="Comma-separated list of required capabilities"),
    materials: Optional[str] = Form(None, description="Comma-separated list of required materials"),
    matching_service: MatchingService = Depends(get_matching_service),
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service),
    http_request: Request = None
):
    """Enhanced file upload matching endpoint."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Validate file type
        if not okh_file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        file_extension = okh_file.filename.lower().split('.')[-1]
        if file_extension not in ['yaml', 'yml', 'json']:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Please upload a YAML (.yaml, .yml) or JSON (.json) file"
            )
        
        # Read and parse the file content
        content = await okh_file.read()
        content_str = content.decode('utf-8')
        
        try:
            if file_extension == 'json':
                okh_data = json.loads(content_str)
            else:  # yaml or yml
                okh_data = yaml.safe_load(content_str)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file format: {str(e)}"
            )
        
        # Convert to OKHManifest
        try:
            okh_manifest = OKHManifest.from_dict(okh_data)
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid OKH manifest: {str(e)}"
            )
        
        # Build OKW filters from form data
        okw_filters = {}
        if access_type:
            okw_filters["access_type"] = access_type
        if facility_status:
            okw_filters["facility_status"] = facility_status
        if location:
            okw_filters["location"] = location
        if capabilities:
            okw_filters["capabilities"] = [cap.strip() for cap in capabilities.split(',')]
        if materials:
            okw_filters["materials"] = [mat.strip() for mat in materials.split(',')]
        
        # Store the OKH manifest
        okh_handler = await storage_service.get_domain_handler("okh")
        await okh_handler.save(okh_manifest)
        
        # Load OKW facilities from storage
        okw_facilities = []
        async for obj in storage_service.manager.list_objects():
            try:
                data = await storage_service.manager.get_object(obj["key"])
                content = data.decode('utf-8')
                
                if obj["key"].endswith(('.yaml', '.yml')):
                    okw_data = yaml.safe_load(content)
                elif obj["key"].endswith('.json'):
                    okw_data = json.loads(content)
                else:
                    continue
                
                from ...models.okw import ManufacturingFacility
                facility = ManufacturingFacility.from_dict(okw_data)
                
                # Apply filters
                if _matches_filters(facility, okw_filters):
                    okw_facilities.append(facility)
                    
            except Exception as e:
                logger.warning(f"Failed to load OKW facility from {obj['key']}: {e}")
                continue
        
        # Find matches
        solutions = await matching_service.find_matches_with_manifest(
            okh_manifest, okw_facilities
        )
        
        # Serialize results using proper SupplyTreeResponse format
        from ..models.supply_tree.response import SupplyTreeResponse, WorkflowResponse, WorkflowNodeResponse, ResourceSnapshotResponse, ProcessStatus
        
        results = []
        for solution in solutions:
            # Convert workflows to API response format
            workflows = {}
            for workflow_id, workflow in solution.tree.workflows.items():
                # Convert nodes to WorkflowNodeResponse format
                nodes = {}
                for node_id in workflow.graph.nodes:
                    node_data = workflow.graph.nodes[node_id]['data']
                    nodes[str(node_id)] = WorkflowNodeResponse(
                        id=node_data.id,
                        name=node_data.name,
                        process_status=ProcessStatus.PENDING,
                        confidence_score=getattr(node_data, 'confidence_score', 1.0),
                        substitution_used=getattr(node_data, 'substitution_used', False),
                        okh_refs=[str(ref) for ref in node_data.okh_refs],
                        okw_refs=[str(ref) for ref in node_data.okw_refs],
                        input_requirements=node_data.input_requirements,
                        output_specifications=node_data.output_specifications,
                        estimated_time=str(node_data.estimated_time) if node_data.estimated_time else None,
                        assigned_facility=node_data.assigned_facility,
                        assigned_equipment=node_data.assigned_equipment,
                        materials=node_data.materials,
                        metadata=node_data.metadata
                    )
                
                # Convert edges to API format
                edges = [{"source": str(source), "target": str(target)} for source, target in workflow.graph.edges]
                
                workflows[str(workflow_id)] = WorkflowResponse(
                    id=workflow_id,
                    name=workflow.name,
                    nodes=nodes,
                    edges=edges,
                    entry_points=[str(ep) for ep in workflow.entry_points],
                    exit_points=[str(ep) for ep in workflow.exit_points]
                )
            
            # Convert snapshots to API format
            snapshots = {}
            for uri, snapshot in solution.tree.snapshots.items():
                snapshots[uri] = ResourceSnapshotResponse(
                    uri=str(snapshot.uri),
                    content=snapshot.content,
                    timestamp=snapshot.timestamp.isoformat() if hasattr(snapshot.timestamp, 'isoformat') else str(snapshot.timestamp)
                )
            
            # Create proper SupplyTreeResponse
            supply_tree_response = SupplyTreeResponse(
                id=solution.tree.id,
                workflows=workflows,
                creation_time=solution.tree.creation_time.isoformat() if hasattr(solution.tree.creation_time, 'isoformat') else str(solution.tree.creation_time),
                confidence=solution.score,
                required_quantity=getattr(solution.tree, 'required_quantity', 1),
                connections=[],  # TODO: Convert connections if they exist
                snapshots=snapshots,
                okh_reference=solution.tree.okh_reference,
                deadline=getattr(solution.tree, 'deadline', None),
                metadata=solution.tree.metadata
            )
            
            results.append({
                "tree": supply_tree_response,
                "score": solution.score,
                "metrics": solution.metrics
            })
        
        return create_success_response(
            message="Matching completed successfully",
            data={
                "solutions": results,
                "total_solutions": len(results),
                "processing_time": 0.0,  # TODO: Calculate actual processing time
                "matching_metrics": {
                    "direct_matches": len(results),
                    "heuristic_matches": 0,
                    "nlp_matches": 0,
                    "llm_matches": 0
                },
                "validation_results": []
            },
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(f"Error in file upload matching: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump()
        )


# Domains endpoints (enhanced version)
@router.get(
    "/domains",
    response_model=PaginatedResponse,
    summary="List Available Domains",
    description="""
    Get a paginated list of available matching domains.
    
    **Features:**
    - Paginated results
    - Sorting and filtering
    - Domain health information
    - Performance metrics
    """
)
@api_endpoint(
    success_message="Domains retrieved successfully",
    include_metrics=True
)
@paginated_response(default_page_size=20, max_page_size=100)
async def list_domains(
    pagination: PaginationParams = Depends(),
    http_request: Request = None
):
    """Enhanced domain listing with pagination and metrics."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Get registered domains
        domains = DomainRegistry.list_domains()
        metadata = DomainRegistry.get_all_metadata()
        
        # Convert to list format
        domain_list = []
        for domain_name in domains:
            domain_metadata = metadata[domain_name]
            domain_list.append({
                "id": domain_name,
                "name": domain_metadata.display_name,
                "description": domain_metadata.description,
                "status": domain_metadata.status.value,
                "version": domain_metadata.version,
                "supported_input_types": list(domain_metadata.supported_input_types),
                "supported_output_types": list(domain_metadata.supported_output_types),
                "documentation_url": domain_metadata.documentation_url,
                "maintainer": domain_metadata.maintainer
            })
        
        # Apply pagination
        total_items = len(domain_list)
        start_idx = (pagination.page - 1) * pagination.page_size
        end_idx = start_idx + pagination.page_size
        paginated_domains = domain_list[start_idx:end_idx]
        
        # Create pagination info
        total_pages = (total_items + pagination.page_size - 1) // pagination.page_size
        
        return create_success_response(
            message="Domains listed successfully",
            data={
                "items": paginated_domains,
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
        
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error listing domains: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e)
            },
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump()
        )


@router.get(
    "/domains/{domain_name}",
    summary="Get Domain Information",
    description="Get detailed information about a specific domain"
)
@api_endpoint(
    success_message="Domain information retrieved successfully",
    include_metrics=True
)
async def get_domain_info(
    domain_name: str,
    http_request: Request = None
):
    """Enhanced domain info endpoint."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        if domain_name not in DomainRegistry.list_domains():
            raise HTTPException(status_code=404, detail=f"Domain '{domain_name}' not found")
        
        metadata = DomainRegistry.get_domain_metadata(domain_name)
        supported_types = DomainRegistry.get_supported_types(domain_name)
        
        return create_success_response(
            message="Domain information retrieved successfully",
            data={
                "name": domain_name,
                "display_name": metadata.display_name,
                "description": metadata.description,
                "version": metadata.version,
                "status": metadata.status.value,
                "supported_input_types": list(metadata.supported_input_types),
                "supported_output_types": list(metadata.supported_output_types),
                "documentation_url": metadata.documentation_url,
                "maintainer": metadata.maintainer,
                "type_mappings": supported_types
            },
            request_id=None
        )
    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(f"Error getting domain info for {domain_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump()
        )


@router.get(
    "/domains/{domain_name}/health",
    summary="Get Domain Health",
    description="Get health status for a specific domain"
)
@api_endpoint(
    success_message="Domain health retrieved successfully",
    include_metrics=True
)
async def get_domain_health(
    domain_name: str,
    http_request: Request = None
):
    """Enhanced domain health endpoint."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        if domain_name not in DomainRegistry.list_domains():
            raise HTTPException(status_code=404, detail=f"Domain '{domain_name}' not found")
        
        # Get domain services
        domain_services = DomainRegistry.get_domain_services(domain_name)
        
        # Basic health check
        health_status = {
            "domain": domain_name,
            "status": "healthy",
            "components": {
                "extractor": {
                    "type": type(domain_services.extractor).__name__,
                    "status": "available"
                },
                "matcher": {
                    "type": type(domain_services.matcher).__name__,
                    "status": "available"
                },
                "validator": {
                    "type": type(domain_services.validator).__name__,
                    "status": "available"
                }
            }
        }
        
        if domain_services.orchestrator:
            health_status["components"]["orchestrator"] = {
                "type": type(domain_services.orchestrator).__name__,
                "status": "available"
            }
        
        return health_status
    except HTTPException:
        raise
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(f"Error getting domain health for {domain_name}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump()
        )


@router.post(
    "/detect-domain",
    summary="Detect Domain from Input",
    description="Detect the appropriate domain from input data"
)
@api_endpoint(
    success_message="Domain detection completed successfully",
    include_metrics=True
)
@track_performance("domain_detection")
async def detect_domain_from_input(
    requirements_data: dict,
    capabilities_data: dict,
    http_request: Request = None
):
    """Enhanced domain detection endpoint."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Create mock objects with the provided data
        class MockRequirements:
            def __init__(self, data):
                self.content = data
                self.domain = data.get('domain')
                self.type = data.get('type')
        
        class MockCapabilities:
            def __init__(self, data):
                self.content = data
                self.domain = data.get('domain')
                self.type = data.get('type')
        
        requirements = MockRequirements(requirements_data)
        capabilities = MockCapabilities(capabilities_data)
        
        # Detect domain
        detection_result = DomainDetector.detect_domain(requirements, capabilities)
        
        return create_success_response(
            message="Domain detection completed successfully",
            data={
                "detected_domain": detection_result.domain,
                "confidence": detection_result.confidence,
                "method": detection_result.method,
                "alternative_domains": detection_result.alternative_domains,
                "is_confident": detection_result.is_confident()
            },
            request_id=request_id
        )
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(f"Error detecting domain: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump()
        )


# Helper functions
async def _extract_okh_manifest(
    request: EnhancedMatchRequest,
    okh_service: OKHService,
    storage_service: StorageService,
    request_id: str
) -> Optional[OKHManifest]:
    """Extract OKH manifest from request."""
    try:
        if request.okh_manifest:
            # If it's already an OKHManifest object, return it directly
            if isinstance(request.okh_manifest, OKHManifest):
                return request.okh_manifest
            # Otherwise, convert from dictionary
            return OKHManifest.from_dict(request.okh_manifest)
        elif request.okh_id:
            return await okh_service.get(str(request.okh_id))
        elif request.okh_url:
            return await okh_service.fetch_from_url(request.okh_url)
        else:
            return None
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_400_BAD_REQUEST,
            request_id=request_id,
            suggestion="Please check the OKH manifest format and try again"
        )
        logger.error(
            f"Error extracting OKH manifest: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.model_dump()
        )


async def _get_filtered_facilities(
    storage_service: StorageService,
    request: EnhancedMatchRequest,
    request_id: str
) -> List[ManufacturingFacility]:
    """Get facilities with applied filters."""
    try:
        # Get all facilities using OKWService
        okw_service = await OKWService.get_instance()
        facilities, total = await okw_service.list(page=1, page_size=1000)
        
        # Apply filters
        filtered_facilities = []
        for facility in facilities:
            # Convert to dict for filtering logic
            if hasattr(facility, 'to_dict'):
                facility_dict = facility.to_dict()
            else:
                facility_dict = facility
            
            # Apply access type filter
            if request.access_type and facility_dict.get("access_type") != request.access_type:
                continue
            
            # Apply facility status filter
            if request.facility_status and facility_dict.get("facility_status") != request.facility_status:
                continue
            
            # Apply location filter
            if request.location and request.location.lower() not in str(facility_dict.get("location", "")).lower():
                continue
            
            filtered_facilities.append(facility)
        
        logger.info(
            f"Filtered facilities: {len(filtered_facilities)} out of {len(facilities)}",
            extra={
                "request_id": request_id,
                "total_facilities": len(facilities),
                "filtered_facilities": len(filtered_facilities),
                "filters_applied": {
                    "access_type": request.access_type,
                    "facility_status": request.facility_status,
                    "location": request.location
                }
            }
        )
        
        return filtered_facilities
        
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error getting filtered facilities: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump()
        )


async def _perform_enhanced_matching(
    matching_service: MatchingService,
    okh_manifest: OKHManifest,
    facilities: List[dict],
    request: EnhancedMatchRequest,
    request_id: str
) -> List[dict]:
    """Perform enhanced matching with LLM support."""
    try:
        # Use the existing matching service with enhanced options
        results = await matching_service.find_matches_with_manifest(
            okh_manifest=okh_manifest,
            facilities=facilities
        )
        
        # Convert results to list of dicts
        matching_results = []
        for result in results:
            if hasattr(result, 'to_dict'):
                matching_results.append(result.to_dict())
            else:
                matching_results.append(result)
        
        logger.info(
            f"Enhanced matching completed: {len(matching_results)} results",
            extra={
                "request_id": request_id,
                "results_count": len(matching_results),
                "llm_used": request.use_llm,
                "min_confidence": request.min_confidence
            }
        )
        
        return matching_results
        
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error in enhanced matching: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump()
        )


async def _process_matching_results(
    results: List[dict],
    request: EnhancedMatchRequest,
    request_id: str
) -> List[dict]:
    """Process and format matching results."""
    try:
        # Filter by confidence threshold (use score if confidence not available)
        filtered_results = [
            result for result in results
            if result.get("confidence", result.get("score", 0)) >= request.min_confidence
        ]
        
        # Sort by confidence/score (highest first)
        filtered_results.sort(key=lambda x: x.get("confidence", x.get("score", 0)), reverse=True)
        
        # Limit results
        if request.max_results:
            filtered_results = filtered_results[:request.max_results]
        
        # Add enhanced metadata
        for i, result in enumerate(filtered_results):
            result["rank"] = i + 1
            result["match_type"] = result.get("match_type", "unknown")
            result["processing_timestamp"] = datetime.now().isoformat()
        
        logger.info(
            f"Processed matching results: {len(filtered_results)} solutions",
            extra={
                "request_id": request_id,
                "original_count": len(results),
                "filtered_count": len(filtered_results),
                "min_confidence": request.min_confidence,
                "max_results": request.max_results
            }
        )
        
        return filtered_results
        
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error processing matching results: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump()
        )


async def _validate_results(
    results: List[dict],
    request_id: str
) -> List[ValidationResult]:
    """Validate matching results."""
    try:
        validation_results = []
        
        for result in results:
            # Basic validation
            is_valid = True
            errors = []
            warnings = []
            suggestions = []
            
            # Check required fields
            if not result.get("facility_id"):
                is_valid = False
                errors.append("Missing facility_id")
            
            if not result.get("confidence"):
                warnings.append("Missing confidence score")
            
            # Check confidence range
            confidence = result.get("confidence", 0)
            if confidence < 0 or confidence > 1:
                is_valid = False
                errors.append(f"Invalid confidence score: {confidence}")
            
            # Generate suggestions
            if confidence < 0.5:
                suggestions.append("Consider reviewing the matching criteria")
            
            validation_result = ValidationResult(
                is_valid=is_valid,
                score=confidence,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
            
            validation_results.append(validation_result)
        
        return validation_results
        
    except Exception as e:
        logger.error(
            f"Error validating results: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        return []


def _matches_filters(facility, filters: dict) -> bool:
    """Check if a facility matches the provided filters"""
    try:
        # Location filter
        if "location" in filters:
            location_filter = filters["location"]
            if "country" in location_filter:
                if facility.location.get("country", "").lower() != location_filter["country"].lower():
                    return False
            if "city" in location_filter:
                if facility.location.get("city", "").lower() != location_filter["city"].lower():
                    return False
        
        # Capability filter
        if "capabilities" in filters:
            required_capabilities = filters["capabilities"]
            facility_capabilities = [cap.get("name", "").lower() for cap in facility.equipment]
            for required_cap in required_capabilities:
                if required_cap.lower() not in facility_capabilities:
                    return False
        
        # Access type filter
        if "access_type" in filters:
            if facility.access_type.lower() != filters["access_type"].lower():
                return False
        
        # Facility status filter
        if "facility_status" in filters:
            if facility.facility_status.lower() != filters["facility_status"].lower():
                return False
        
        return True
    except Exception as e:
        logger.warning(f"Error applying filters to facility {facility.name}: {e}")
        return True  # Default to including the facility if filter fails
