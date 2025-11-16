"""
Consolidated match API routes with standardized patterns.

This module combines the functionality from both match.py and match_enhanced.py
into a single, standardized API route file with enhanced error handling,
request validation, and response formatting.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request, status
from uuid import UUID
from typing import Optional, List, Dict, Any
import json
import yaml
from datetime import datetime

# Import new standardized components
from ..models.base import (
    PaginationParams,
    PaginatedResponse,
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
from ..models.match.request import MatchRequest, ValidateMatchRequest, SimulateRequest
from ..models.match.response import MatchResponse, SimulateResponse
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
    status_code=status.HTTP_200_OK,
    summary="Enhanced Requirements Matching (Domain-Aware)",
    description="""
    Enhanced endpoint for matching requirements with capabilities across multiple domains.
    
    **Supported Domains:**
    - **Manufacturing**: Match OKH requirements with OKW capabilities
    - **Cooking**: Match recipe requirements with kitchen capabilities
    
    **Domain Auto-Detection:**
    The endpoint automatically detects the domain from the input data structure:
    - Manufacturing domain: Detected from OKH manifest structure (title, version, manufacturing_specs)
    - Cooking domain: Detected from recipe structure (ingredients, instructions, name)
    
    You can also explicitly specify the domain using the `domain` field in the request.
    
    **This endpoint provides:**
    - Standardized request/response formats
    - LLM integration support
    - Enhanced error handling
    - Performance metrics
    - Validation
    - Domain-aware matching logic
    
    **Features:**
    - Support for multiple input formats (manifest/recipe, ID, URL)
    - Domain auto-detection or explicit domain override
    - Advanced filtering options
    - LLM-powered matching capabilities
    - Real-time performance tracking
    - Detailed validation results
    - Unique facility IDs in match results
    """
)
@api_endpoint(
    success_message="Matching completed successfully",
    include_metrics=True,
    track_llm=True
)
@validate_request(MatchRequest)
@track_performance("enhanced_matching")
@llm_endpoint(
    default_provider="anthropic",
    default_model="claude-sonnet-4-5",
    track_costs=True
)
async def match_requirements_to_capabilities(
    request: MatchRequest,
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
        Enhanced match response with data
    """
    request_id = getattr(http_request.state, 'request_id', None)
    start_time = datetime.now()
    
    try:
        # 1. Detect domain from request
        domain = await _detect_domain_from_request(request)
        logger.info(f"Detected domain: {domain}", extra={"request_id": request_id, "domain": domain})
        
        # 2. Extract requirements based on domain
        if domain == "manufacturing":
            # Extract OKH manifest
            okh_manifest = await _extract_okh_manifest(
                request, okh_service, storage_service, request_id
            )
            
            if not okh_manifest:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Must provide either okh_manifest, okh_id, or okh_url"
                )
            
            requirements_data = okh_manifest
        elif domain == "cooking":
            # Extract recipe
            recipe = await _extract_recipe(
                request, storage_service, request_id
            )
            
            if not recipe:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Must provide either recipe, recipe_id, or recipe_url"
                )
            
            requirements_data = recipe
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported domain: {domain}"
            )
        
        # 3. Get available facilities with filtering
        facilities = await _get_filtered_facilities(
            storage_service, request, request_id, domain=domain
        )
        
        if not facilities:
            logger.warning(
                f"No facilities found matching criteria",
                extra={
                    "request_id": request_id,
                    "domain": domain,
                    "filters": {
                        "access_type": request.access_type,
                        "facility_status": request.facility_status,
                        "location": request.location
                    }
                }
            )
        
        # 4. Perform matching with enhanced options
        matching_results = await _perform_enhanced_matching(
            matching_service, requirements_data, facilities, request, request_id, domain=domain
        )
        
        # 5. Process and format results
        solutions = await _process_matching_results(
            matching_results, request, request_id, domain=domain
        )
        
        # 5. Calculate processing metrics
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 6. Create enhanced response
        validation_results = await _validate_results(solutions, request_id)
        # Convert ValidationResult objects to dicts for JSON serialization
        validation_results_dicts = [
            result.model_dump() if hasattr(result, 'model_dump') else result
            for result in validation_results
        ]
        
        response_data = {
            "solutions": solutions,
            "total_solutions": len(solutions),
            "processing_time": processing_time,
            "matching_metrics": {
                "direct_matches": len([s for s in solutions if s.get("tree", {}).get("match_type") == "direct"]),
                "heuristic_matches": len([s for s in solutions if s.get("tree", {}).get("match_type") == "heuristic"]),
                "nlp_matches": len([s for s in solutions if s.get("tree", {}).get("match_type") == "nlp"]),
                "llm_matches": len([s for s in solutions if s.get("tree", {}).get("match_type") == "llm"])
            },
            "validation_results": validation_results_dicts
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
            detail=error_response.model_dump(mode='json')
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
    storage_service: StorageService = Depends(get_storage_service),
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
        
        # Load OKH manifest from storage
        okh_handler = await storage_service.get_domain_handler("okh")
        okh_manifest = await okh_handler.load(request.okh_id)
        
        if not okh_manifest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKH manifest {request.okh_id} not found"
            )
        
        # Get domain from OKH manifest or default to manufacturing
        domain = "manufacturing"  # Default, could be detected from manifest
        
        # Get domain validator from registry
        if not DomainRegistry.is_domain_registered(domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Domain {domain} is not registered"
            )
        
        domain_services = DomainRegistry.get_domain_services(domain)
        validator = domain_services.validator
        
        # Create validation context
        from src.core.validation.context import ValidationContext
        context = ValidationContext(
            name=f"match_validation_{request.okh_id}",
            domain=domain,
            quality_level=quality_level or "professional",
            strict_mode=strict_mode
        )
        
        # Validate OKH manifest
        okh_validation = await validator.validate(okh_manifest, context)
        
        # Validate supply tree structure and compatibility
        supply_tree_errors = []
        supply_tree_warnings = []
        supply_tree_suggestions = []
        
        # TODO: Load actual supply tree from storage if available and validate it
        # For now, we'll just validate the OKH manifest
        
        # Convert validation result to API format
        from src.core.api.models.base import ErrorDetail, ErrorCode
        all_errors = [
            ErrorDetail(
                message=error.message,
                field=error.field,
                code=ErrorCode.VALIDATION_ERROR if error.code is None else ErrorCode(error.code) if isinstance(error.code, str) else error.code
            )
            for error in okh_validation.errors
        ] + [
            ErrorDetail(message=err, code=ErrorCode.VALIDATION_ERROR) if isinstance(err, str) else err
            for err in supply_tree_errors
        ]
        all_warnings = [warning.message for warning in okh_validation.warnings] + supply_tree_warnings
        all_suggestions = supply_tree_suggestions  # Could add suggestions from validation
        
        # Calculate validation score
        okh_score = okh_validation.metadata.get("completeness_score", 1.0) if okh_validation.valid else 0.0
        supply_tree_score = 1.0  # Placeholder, would calculate from supply tree validation
        validation_score = (okh_score + supply_tree_score) / 2.0
        
        # Apply strict mode: treat warnings as errors
        if strict_mode and all_warnings:
            # Convert warnings to errors in strict mode
            from src.core.api.models.base import ErrorCode
            all_errors.extend([
                ErrorDetail(message=w, code=ErrorCode.VALIDATION_ERROR) if isinstance(w, str) else w
                for w in all_warnings
            ])
            all_warnings = []
            # Reduce score if there were warnings
            validation_score *= 0.9
        
        is_valid = len(all_errors) == 0 and okh_validation.valid
        
        return ValidationResult(
            is_valid=is_valid,
            score=validation_score,
            errors=all_errors,
            warnings=all_warnings,
            suggestions=all_suggestions,
            metadata={
                "okh_id": str(request.okh_id),
                "supply_tree_id": str(request.supply_tree_id),
                "validation_criteria": request.validation_criteria,
                "quality_level": quality_level,
                "strict_mode": strict_mode,
                "okh_validation_score": okh_score,
                "supply_tree_validation_score": supply_tree_score
            }
        )
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
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
            detail=error_response.model_dump(mode='json')
        )


# File upload endpoint (enhanced version)
@router.post(
    "/upload", 
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
    start_time = datetime.now()
    
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
        # Convert Set to List for iteration
        solutions = list(solutions)
        
        # Serialize simplified SupplyTree results
        results = []
        for solution in solutions:
            # Use the simplified to_dict method from SupplyTreeSolution
            results.append(solution.to_dict())
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return create_success_response(
            message="Matching completed successfully",
            data={
                "solutions": results,
                "total_solutions": len(results),
                "processing_time": processing_time,
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
            detail=error_response.model_dump(mode='json')
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
            detail=error_response.model_dump(mode='json')
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
            detail=error_response.model_dump(mode='json')
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
            detail=error_response.model_dump(mode='json')
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
            detail=error_response.model_dump(mode='json')
        )


# Helper functions
async def _detect_domain_from_request(request: MatchRequest) -> str:
    """Detect domain from request input"""
    # If domain is explicitly provided, use it
    if request.domain:
        return request.domain
    
    # Detect from input type
    if request.okh_id or request.okh_manifest or request.okh_url:
        return "manufacturing"
    elif request.recipe_id or request.recipe or request.recipe_url:
        return "cooking"
    else:
        # Default to manufacturing for backward compatibility
        return "manufacturing"


async def _extract_okh_manifest(
    request: MatchRequest,
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
            detail=error_response.model_dump(mode='json')
        )


async def _extract_recipe(
    request: MatchRequest,
    storage_service: StorageService,
    request_id: str
) -> Optional[dict]:
    """Extract recipe from request."""
    try:
        if request.recipe:
            # Recipe is already provided as dict
            return request.recipe
        elif request.recipe_id:
            # Load recipe from storage by ID
            # For now, we'll need to search storage for the recipe
            # This is a simplified implementation - in production, you'd have a recipe service
            async for obj in storage_service.manager.list_objects():
                if 'recipe' in obj["key"].lower():
                    try:
                        data = await storage_service.manager.get_object(obj["key"])
                        content = data.decode('utf-8')
                        recipe_data = json.loads(content)
                        # Check if this is the recipe we're looking for
                        # For now, we'll just return the first recipe found
                        # In production, you'd match by ID
                        return recipe_data
                    except Exception:
                        continue
            return None
        elif request.recipe_url:
            # Fetch recipe from URL
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(request.recipe_url)
                response.raise_for_status()
                return response.json()
        else:
            return None
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_400_BAD_REQUEST,
            request_id=request_id,
            suggestion="Please check the recipe format and try again"
        )
        logger.error(
            f"Error extracting recipe: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.model_dump(mode='json')
        )


async def _get_filtered_facilities(
    storage_service: StorageService,
    request: MatchRequest,
    request_id: str,
    domain: str = "manufacturing"
) -> List[Any]:
    """Get facilities with applied filters. Returns ManufacturingFacility for manufacturing domain, dict for cooking domain."""
    try:
        if domain == "manufacturing":
            # Get all facilities using OKWService with proper pagination
            okw_service = await OKWService.get_instance()
            
            # Get all facilities by paginating through all pages
            all_facilities = []
            page = 1
            page_size = 1000
            
            while True:
                facilities_batch, _ = await okw_service.list(page=page, page_size=page_size)
                all_facilities.extend(facilities_batch)
                
                # If we got fewer facilities than page_size, we've reached the end
                if len(facilities_batch) < page_size:
                    break
                    
                page += 1
            
            facilities = all_facilities
            total = len(all_facilities)
        elif domain == "cooking":
            # Load kitchens from storage
            all_facilities = []
            async for obj in storage_service.manager.list_objects():
                try:
                    # Only process kitchen files
                    if 'kitchen' not in obj["key"].lower():
                        continue
                    
                    data = await storage_service.manager.get_object(obj["key"])
                    content = data.decode('utf-8')
                    kitchen_data = json.loads(content)
                    
                    # Ensure kitchen has an ID - extract from storage key if not present
                    if "id" not in kitchen_data:
                        # Extract ID from storage key format: {name}-{id}-kitchen.json
                        key_parts = obj["key"].split("-")
                        if len(key_parts) >= 2:
                            # Try to extract ID from key (format: name-id-kitchen.json)
                            potential_id = key_parts[-2] if key_parts[-1].startswith("kitchen") else None
                            if potential_id and len(potential_id) == 8:  # UUID short format
                                # Generate full UUID from short ID or use as-is
                                kitchen_data["id"] = potential_id
                            else:
                                # Generate new UUID if can't extract from key
                                from uuid import uuid4
                                kitchen_data["id"] = str(uuid4())
                        else:
                            # Generate new UUID if key format is unexpected
                            from uuid import uuid4
                            kitchen_data["id"] = str(uuid4())
                    
                    # Store storage key for reference
                    kitchen_data["storage_key"] = obj["key"]
                    
                    all_facilities.append(kitchen_data)
                except Exception as e:
                    logger.warning(f"Failed to load kitchen from {obj['key']}: {e}")
                    continue
            
            facilities = all_facilities
            total = len(all_facilities)
        else:
            raise ValueError(f"Unsupported domain: {domain}")
        
        logger.info(
            f"Loaded {total} facilities for {domain} domain",
            extra={
                "request_id": request_id,
                "total_facilities": total,
                "domain": domain
            }
        )
        
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
            detail=error_response.model_dump(mode='json')
        )


async def _perform_enhanced_matching(
    matching_service: MatchingService,
    requirements_data: Any,
    facilities: List[Any],
    request: MatchRequest,
    request_id: str,
    domain: str = "manufacturing"
) -> List[dict]:
    """Perform enhanced matching with LLM support."""
    try:
        if domain == "manufacturing":
            # Use the existing matching service for manufacturing
            if not isinstance(requirements_data, OKHManifest):
                raise ValueError("Requirements data must be OKHManifest for manufacturing domain")
            
            solutions = await matching_service.find_matches_with_manifest(
                okh_manifest=requirements_data,
                facilities=facilities
            )
            
            # Convert SupplyTreeSolution objects to dict format expected by API
            results = []
            for solution in solutions:
                # Extract facility information from the solution
                facility_name = solution.tree.facility_name if solution.tree.facility_name else "Unknown Facility"
                
                # Try to find the facility in the facilities list to get its ID
                facility_id = None
                facility_data = None
                for facility in facilities:
                    if hasattr(facility, 'name') and facility.name == facility_name:
                        facility_id = str(facility.id)
                        facility_data = facility.to_dict()
                        break
                    elif isinstance(facility, dict) and facility.get('name') == facility_name:
                        facility_id = facility.get('id', 'unknown')
                        facility_data = facility
                        break
                
                # If we couldn't find the facility, try to extract from tree metadata
                if not facility_id:
                    facility_id = solution.tree.metadata.get('facility_id') if solution.tree.metadata else None
                    if not facility_id:
                        # Generate a placeholder ID
                        from uuid import uuid4
                        facility_id = str(uuid4())[:8]
                
                # Create solution dict in expected format
                solution_dict = {
                    "tree": solution.tree.to_dict(),
                    "facility": facility_data if facility_data else {},
                    "facility_id": facility_id,
                    "facility_name": facility_name,
                    "match_type": "manufacturing",
                    "confidence": solution.tree.confidence_score if solution.tree.confidence_score else solution.score,
                    "score": solution.score,
                    "metrics": solution.metrics
                }
                results.append(solution_dict)
        elif domain == "cooking":
            # Use cooking domain extractor and matcher
            from ...domains.cooking.extractors import CookingExtractor
            from ...domains.cooking.matchers import CookingMatcher
            
            extractor = CookingExtractor()
            matcher = CookingMatcher()
            
            # Extract requirements from recipe
            extraction_result = extractor.extract_requirements(requirements_data)
            requirements = extraction_result.data if extraction_result.data else None
            
            if not requirements:
                raise ValueError("Failed to extract requirements from recipe")
            
            # Match against each kitchen
            results = []
            for kitchen in facilities:
                # Extract capabilities from kitchen
                capabilities_result = extractor.extract_capabilities(kitchen)
                capabilities = capabilities_result.data if capabilities_result.data else None
                
                if not capabilities:
                    continue
                
                # Generate supply tree with kitchen and recipe names
                kitchen_name = kitchen.get("name", "Unknown Kitchen")
                recipe_name = requirements_data.get("name", "Unknown Recipe")
                supply_tree = matcher.generate_supply_tree(requirements, capabilities, kitchen_name, recipe_name)
                
                # Create a simple solution dict with unique ID
                solution = {
                    "tree": supply_tree.to_dict() if hasattr(supply_tree, 'to_dict') else supply_tree,
                    "facility": kitchen,
                    "facility_id": kitchen.get("id", kitchen.get("storage_key", "unknown")),
                    "facility_name": kitchen.get("name", "Unknown Kitchen"),
                    "match_type": "cooking",
                    "confidence": supply_tree.confidence_score if hasattr(supply_tree, 'confidence_score') else 0.8
                }
                results.append(solution)
        else:
            raise ValueError(f"Unsupported domain: {domain}")
        
        # Results are already in dict format (manufacturing) or list of dicts (cooking)
        # No need for additional conversion
        matching_results = results
        
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
            detail=error_response.model_dump(mode='json')
        )


async def _process_matching_results(
    results: List[dict],
    request: MatchRequest,
    request_id: str,
    domain: str = "manufacturing"
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
            detail=error_response.model_dump(mode='json')
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


@router.post(
    "/simulate",
    response_model=SimulateResponse,
    summary="Simulate Supply Tree Execution",
    description="""
    Simulate the execution of a supply tree.
    
    This endpoint simulates the execution of a supply tree by analyzing
    resource availability, critical paths, and potential bottlenecks.
    """
)
@api_endpoint(
    success_message="Simulation completed successfully",
    include_metrics=True
)
@track_performance("match_simulate")
async def simulate_supply_tree(
    request: SimulateRequest,
    http_request: Request = None
):
    """Simulate execution of a supply tree."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    start_time = datetime.now()
    
    try:
        # Extract supply tree and parameters
        supply_tree = request.supply_tree
        parameters = request.parameters
        
        # Parse start time
        try:
            start_time_parsed = datetime.fromisoformat(parameters.start_time.replace('Z', '+00:00'))
        except ValueError:
            error_response = create_error_response(
                error=f"Invalid start_time format: {parameters.start_time}",
                status_code=status.HTTP_400_BAD_REQUEST,
                request_id=request_id,
                suggestion="Please provide start_time in ISO format (e.g., '2023-01-01T00:00:00Z')"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.model_dump(mode='json')
            )
        
        # Extract estimated time from supply tree
        estimated_time_str = supply_tree.get("estimated_time", "2 weeks")
        
        # Simple time estimation (in a full implementation, this would be more sophisticated)
        # For now, we'll add a fixed duration to the start time
        days_to_add = 7  # Default to 1 week
        if "week" in estimated_time_str.lower():
            try:
                weeks = int(estimated_time_str.split()[0])
                days_to_add = weeks * 7
            except (ValueError, IndexError):
                pass
        elif "day" in estimated_time_str.lower():
            try:
                days_to_add = int(estimated_time_str.split()[0])
            except (ValueError, IndexError):
                pass
        
        from datetime import timedelta
        completion_time = start_time_parsed + timedelta(days=days_to_add)
        
        # Calculate critical path (simplified - in full implementation would analyze workflow DAG)
        critical_path = []
        if supply_tree.get("capabilities_used"):
            for i, capability in enumerate(supply_tree["capabilities_used"][:3]):  # Limit to first 3
                critical_path.append({
                    "step": capability,
                    "duration": f"{days_to_add // len(supply_tree['capabilities_used'])} days" if supply_tree["capabilities_used"] else "1 day"
                })
        
        # Identify bottlenecks (simplified)
        bottlenecks = []
        resource_utilization = {
            "equipment": {},
            "labor": {}
        }
        
        # If resource availability is provided, calculate utilization
        if parameters.resource_availability:
            for resource, availability in parameters.resource_availability.items():
                # Simplified utilization calculation
                utilization = 0.75  # Default
                if isinstance(availability, dict) and "capacity" in availability:
                    capacity = availability.get("capacity", 1)
                    if capacity > 0:
                        utilization = min(1.0, 0.75 / capacity)
                
                if utilization > 0.9:
                    bottlenecks.append({
                        "resource": resource,
                        "utilization": round(utilization, 2),
                        "impact": "high"
                    })
                
                # Categorize as equipment or labor
                if "machine" in resource.lower() or "equipment" in resource.lower():
                    resource_utilization["equipment"][resource] = round(utilization, 2)
                else:
                    resource_utilization["labor"][resource] = round(utilization, 2)
        
        logger.info(
            f"Simulation completed successfully",
            extra={
                "request_id": request_id,
                "supply_tree_id": supply_tree.get("id"),
                "completion_time": completion_time.isoformat(),
                "bottlenecks_count": len(bottlenecks)
            }
        )
        
        return SimulateResponse(
            status="success",
            message="Simulation completed successfully",
            timestamp=datetime.now(),
            request_id=request_id,
            completion_time=completion_time.isoformat(),
            critical_path=critical_path,
            bottlenecks=bottlenecks,
            resource_utilization=resource_utilization
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
            f"Error simulating supply tree: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )
