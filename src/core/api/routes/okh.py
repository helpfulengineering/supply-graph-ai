from fastapi import APIRouter, HTTPException, Query, Path, Depends, status, UploadFile, File, Form, Request
from typing import Optional, List
from uuid import UUID
import json
import yaml
from datetime import datetime
from pydantic import Field

# Import new standardized components
from ..models.base import (
    BaseAPIRequest, 
    SuccessResponse, 
    PaginationParams,
    PaginatedResponse,
    LLMRequestMixin,
    LLMResponseMixin,
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

# Import existing models and services (now properly used through inheritance)
from ..models.okh.request import (
    OKHCreateRequest, 
    OKHUpdateRequest, 
    OKHValidateRequest,
    OKHExtractRequest,
    OKHGenerateRequest
)
from ..models.okh.response import (
    OKHResponse, 
    OKHExtractResponse,
    OKHUploadResponse,
    OKHGenerateResponse
)
from ...services.okh_service import OKHService
from ...services.storage_service import StorageService
from ...utils.logging import get_logger
from src.config import settings

# Set up logging
logger = get_logger(__name__)

# Create router with standardized patterns
router = APIRouter(
    tags=["okh"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)

# Enhanced request models that inherit from original models
class EnhancedOKHCreateRequest(OKHCreateRequest, BaseAPIRequest, LLMRequestMixin):
    """Enhanced OKH create request with standardized fields and LLM support."""
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Arduino-based IoT Sensor Node",
                "repo": "https://github.com/example/iot-sensor",
                "version": "1.0.0",
                "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
                "licensor": "John Doe",
                "documentation_language": "en",
                "function": "IoT sensor node for environmental monitoring",
                "description": "A simple IoT sensor node based on Arduino",
                "intended_use": "Environmental monitoring and data collection",
                "keywords": ["iot", "sensor", "arduino", "environmental"],
                "project_link": "https://github.com/example/iot-sensor",
                "manufacturing_files": [
                    {"name": "pcb_design.kicad", "type": "design", "url": "https://github.com/example/iot-sensor/pcb.kicad"}
                ],
                "design_files": [
                    {"name": "enclosure.stl", "type": "3d_model", "url": "https://github.com/example/iot-sensor/enclosure.stl"}
                ],
                "tool_list": ["3D Printer", "Soldering Iron", "Multimeter"],
                "manufacturing_processes": ["3D Printing", "PCB Assembly", "Soldering"],
                "materials": [
                    {"name": "Arduino Nano", "quantity": 1, "specifications": "ATmega328P microcontroller"}
                ],
                "manufacturing_specs": {
                    "process_requirements": [
                        {"process_name": "PCB Assembly", "parameters": {}}
                    ]
                },
                "parts": [
                    {"name": "Arduino Nano", "quantity": 1, "specifications": "ATmega328P"}
                ],
                "metadata": {"category": "electronics", "difficulty": "beginner"},
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-3-sonnet",
                "quality_level": "professional",
                "strict_mode": False
            }
        }


class EnhancedOKHResponse(OKHResponse, SuccessResponse, LLMResponseMixin):
    """Enhanced OKH response with standardized fields and LLM information."""
    
    # Additional fields for enhanced response
    processing_time: float = 0.0
    validation_results: Optional[List[ValidationResult]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "00000000-0000-0000-0000-000000000000",
                "title": "Arduino-based IoT Sensor Node",
                "version": "1.0.0",
                "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
                "licensor": "John Doe",
                "documentation_language": "en",
                "function": "IoT sensor node for environmental monitoring",
                "repo": "https://github.com/example/iot-sensor",
                "description": "A simple IoT sensor node based on Arduino",
                "intended_use": "Environmental monitoring and data collection",
                "keywords": ["iot", "sensor", "arduino", "environmental"],
                "project_link": "https://github.com/example/iot-sensor",
                "manufacturing_files": [
                    {"name": "pcb_design.kicad", "type": "design", "url": "https://github.com/example/iot-sensor/pcb.kicad"}
                ],
                "design_files": [
                    {"name": "enclosure.stl", "type": "3d_model", "url": "https://github.com/example/iot-sensor/enclosure.stl"}
                ],
                "tool_list": ["3D Printer", "Soldering Iron", "Multimeter"],
                "manufacturing_processes": ["3D Printing", "PCB Assembly", "Soldering"],
                "materials": [
                    {"name": "Arduino Nano", "quantity": 1, "specifications": "ATmega328P microcontroller"}
                ],
                "manufacturing_specs": {
                    "process_requirements": [
                        {"process_name": "PCB Assembly", "parameters": {}}
                    ]
                },
                "parts": [
                    {"name": "Arduino Nano", "quantity": 1, "specifications": "ATmega328P"}
                ],
                "metadata": {"category": "electronics", "difficulty": "beginner"},
                "status": "success",
                "message": "OKH operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "processing_time": 1.25,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.012,
                "data": {},
                "validation_results": []
            }
        }


# Service dependencies
async def get_okh_service() -> OKHService:
    """Get OKH service instance."""
    return await OKHService.get_instance()


async def get_storage_service() -> StorageService:
    """Get storage service instance."""
    return await StorageService.get_instance()

@router.post(
    "/create", 
    response_model=EnhancedOKHResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create OKH Manifest",
    description="""
    Create a new OpenKnowHow manifest with enhanced capabilities.
    
    This endpoint provides:
    - Standardized request/response formats
    - LLM integration support
    - Enhanced error handling
    - Performance metrics
    - Comprehensive validation
    
    **Features:**
    - Support for LLM-enhanced manifest creation
    - Advanced validation options
    - Real-time performance tracking
    - Detailed validation results
    """
)
@api_endpoint(
    success_message="OKH manifest created successfully",
    include_metrics=True,
    track_llm=True
)
@validate_request(EnhancedOKHCreateRequest)
@track_performance("okh_creation")
@llm_endpoint(
    default_provider="anthropic",
    default_model="claude-3-sonnet",
    track_costs=True
)
async def create_okh(
    request: EnhancedOKHCreateRequest,
    http_request: Request,
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Enhanced OKH manifest creation with standardized patterns.
    
    Args:
        request: Enhanced OKH create request with standardized fields
        http_request: HTTP request object for tracking
        okh_service: OKH service dependency
        
    Returns:
        Enhanced OKH response with comprehensive data
    """
    request_id = getattr(http_request.state, 'request_id', None)
    start_time = datetime.utcnow()
    
    try:
        # Call service to create OKH manifest
        result = await okh_service.create(request.model_dump())
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Create enhanced response using the proper OKHResponse structure
        result_dict = result.to_dict() if hasattr(result, 'to_dict') else result
        response_data = {
            **result_dict,  # Include all OKHResponse fields
            "processing_time": processing_time,
            "validation_results": await _validate_okh_result(result, request_id)
        }
        
        logger.info(
            f"OKH manifest created successfully",
            extra={
                "request_id": request_id,
                "processing_time": processing_time,
                "llm_used": request.use_llm
            }
        )
        
        return response_data
        
    except ValueError as e:
        # Handle validation errors using standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id=request_id,
            suggestion="Please check the input data and try again"
        )
        logger.error(
            f"Validation error creating OKH manifest: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_response.model_dump()
        )
    except Exception as e:
        # Log unexpected errors using standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error creating OKH manifest: {str(e)}",
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

@router.get("/{id}", response_model=OKHResponse)
async def get_okh(
    id: UUID = Path(..., title="The ID of the OKH manifest"),
    component: Optional[str] = Query(None, description="Specific component to retrieve"),
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Get an OKH manifest by ID
    
    Retrieves a specific OpenKnowHow manifest by its unique identifier.
    Optionally retrieves only a specific component of the manifest.
    """
    try:
        # Call service to get OKH manifest
        result = await okh_service.get(id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKH manifest with ID {id} not found"
            )
        
        # Convert OKHManifest to OKHResponse
        manifest_dict = result.to_dict()
        return OKHResponse(**manifest_dict)
    except ValueError as e:
        # Handle invalid parameters
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error retrieving OKH manifest {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the OKH manifest"
        )

@router.get(
    "", 
    response_model=PaginatedResponse,
    summary="List OKH Manifests",
    description="""
    Get a paginated list of OpenKnowHow manifests with enhanced capabilities.
    
    **Features:**
    - Paginated results with sorting and filtering
    - Enhanced error handling
    - Performance metrics
    - Comprehensive validation
    """
)
@api_endpoint(
    success_message="OKH manifests retrieved successfully",
    include_metrics=True
)
@paginated_response(default_page_size=20, max_page_size=100)
async def list_okh(
    pagination: PaginationParams = Depends(),
    filter: Optional[str] = Query(None, description="Filter criteria (e.g., 'title=contains:Hardware')"),
    okh_service: OKHService = Depends(get_okh_service),
    http_request: Request = None
):
    """Enhanced OKH manifest listing with pagination and metrics."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Parse filter parameter if provided
        filter_params = {}
        if filter:
            # Simple parsing for filter format: field=operator:value
            # For example: title=contains:Hardware
            parts = filter.split('=', 1)
            if len(parts) == 2:
                field, op_value = parts
                op_parts = op_value.split(':', 1)
                if len(op_parts) == 2:
                    op, value = op_parts
                    filter_params = {
                        "field": field,
                        "operator": op,
                        "value": value
                    }
        
        # Call service to list OKH manifests
        manifests, total = await okh_service.list(pagination.page, pagination.page_size, filter_params)
        
        # Convert OKHManifest objects to dict format
        results = []
        for manifest in manifests:
            # Convert OKHManifest to dict
            manifest_dict = manifest.to_dict() if hasattr(manifest, 'to_dict') else manifest
            results.append(manifest_dict)
        
        # Create pagination info
        total_pages = (total + pagination.page_size - 1) // pagination.page_size
        
        return create_success_response(
            message="OKH manifests listed successfully",
            data={
                "items": results,
                "pagination": {
                    "page": pagination.page,
                    "page_size": pagination.page_size,
                    "total_items": total,
                    "total_pages": total_pages,
                    "has_next": pagination.page < total_pages,
                    "has_previous": pagination.page > 1
                }
            },
            request_id=request_id
        )
        
    except ValueError as e:
        # Handle invalid parameters
        logger.error(
            f"Invalid parameters for OKH listing: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
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
            f"Error listing OKH manifests: {str(e)}",
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

@router.put("/{id}", response_model=OKHResponse)
async def update_okh(
    request: OKHUpdateRequest,
    id: UUID = Path(..., title="The ID of the OKH manifest"),
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Update an OKH manifest
    
    Updates an existing OpenKnowHow manifest with the provided data.
    """
    try:
        # Check if manifest exists
        existing = await okh_service.get(id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKH manifest with ID {id} not found"
            )
        
        # Call service to update OKH manifest
        result = await okh_service.update(id, request.model_dump())
        return result
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error updating OKH manifest {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the OKH manifest"
        )

@router.delete("/{id}", response_model=SuccessResponse)
async def delete_okh(
    id: UUID = Path(..., title="The ID of the OKH manifest"),
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Delete an OKH manifest
    
    Deletes an OpenKnowHow manifest by its unique identifier.
    """
    try:
        # Check if manifest exists
        existing = await okh_service.get(id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKH manifest with ID {id} not found"
            )
        
        # Call service to delete OKH manifest
        success = await okh_service.delete(id)
        
        return SuccessResponse(
            success=success,
            message=f"OKH manifest with ID {id} deleted successfully"
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error deleting OKH manifest {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the OKH manifest"
        )

@router.post(
    "/validate", 
    response_model=ValidationResult,
    summary="Validate OKH Manifest",
    description="""
    Validate an OKH manifest with domain-aware validation and enhanced capabilities.
    
    Validates an OpenKnowHow manifest against domain-specific validation rules
    based on the specified quality level. The validation framework provides:
    
    - **Hobby Level**: Relaxed validation for personal projects
    - **Professional Level**: Standard validation for commercial use  
    - **Medical Level**: Strict validation for medical device manufacturing
    
    Returns detailed validation results including errors, warnings, and
    completeness scoring.
    """
)
@api_endpoint(
    success_message="OKH validation completed successfully",
    include_metrics=True
)
@track_performance("okh_validation")
async def validate_okh(
    request: OKHValidateRequest,
    quality_level: Optional[str] = Query("professional", description="Quality level: hobby, professional, or medical"),
    strict_mode: Optional[bool] = Query(False, description="Enable strict validation mode"),
    okh_service: OKHService = Depends(get_okh_service),
    http_request: Request = None
):
    """Enhanced OKH validation with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Use quality_level from query parameter, fallback to validation_context
        validation_context = quality_level or request.validation_context or "professional"
        
        logger.info(
            "Validating OKH manifest",
            extra={
                "validation_context": validation_context,
                "strict_mode": strict_mode,
                "request_id": request_id
            }
        )
        
        # Call service to validate OKH manifest with enhanced parameters
        result = await okh_service.validate(
            request.content, 
            validation_context,
            strict_mode
        )
        
        # Convert to ValidationResult format if needed
        if hasattr(result, 'to_dict'):
            result_dict = result.to_dict()
        else:
            result_dict = result
        
        return ValidationResult(
            is_valid=result_dict.get("is_valid", True),
            score=result_dict.get("score", 1.0),
            errors=result_dict.get("errors", []),
            warnings=result_dict.get("warnings", []),
            suggestions=result_dict.get("suggestions", []),
            metadata={
                "validation_context": validation_context,
                "strict_mode": strict_mode,
                "request_id": request_id
            }
        )
        
    except ValueError as e:
        # Handle validation errors using standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id=request_id,
            suggestion="Please check the validation parameters and try again"
        )
        logger.error(
            f"Validation error in OKH validation: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_response.model_dump()
        )
    except Exception as e:
        # Log unexpected errors using standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error validating OKH manifest: {str(e)}",
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

@router.post("/extract", response_model=OKHExtractResponse)
async def extract_requirements(
    request: OKHExtractRequest,
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Extract requirements from an OKH object
    
    Extracts process requirements from an OpenKnowHow object for matching.
    """
    try:
        # Call service to extract requirements
        requirements = await okh_service.extract_requirements(request.content)
        
        return OKHExtractResponse(requirements=requirements)
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error extracting requirements: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while extracting requirements"
        )

@router.post("/upload", response_model=OKHUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_okh_file(
    okh_file: UploadFile = File(..., description="OKH file (YAML or JSON)"),
    description: Optional[str] = Form(None, description="Optional description for the uploaded OKH"),
    tags: Optional[str] = Form(None, description="Comma-separated list of tags"),
    validation_context: Optional[str] = Form(None, description="Validation context (e.g., 'manufacturing', 'hobby')"),
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Upload an OKH file
    
    Accepts a file upload (YAML or JSON) containing an OKH manifest,
    validates it, and stores it for use in matching operations.
    """
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
            from ...models.okh import OKHManifest
            okh_manifest = OKHManifest.from_dict(okh_data)
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid OKH manifest: {str(e)}"
            )
        
        # Validate the manifest
        try:
            okh_manifest.validate()
        except ValueError as e:
            raise HTTPException(
                status_code=400, 
                detail=f"OKH validation failed: {str(e)}"
            )
        
        # Store the OKH manifest
        try:
            result = await okh_service.create(okh_manifest.to_dict())
        except Exception as e:
            logger.error(f"Error storing OKH manifest: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error storing OKH manifest: {str(e)}"
            )
        
        # Convert result to OKHResponse format
        result_dict = result.to_dict()
        okh_response = OKHResponse(**result_dict)
        
        return OKHUploadResponse(
            success=True,
            message=f"OKH file '{okh_file.filename}' uploaded and stored successfully",
            okh=okh_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading OKH file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/generate-from-url", response_model=OKHGenerateResponse)
async def generate_from_url(
    request: OKHGenerateRequest,
    okh_service: OKHService = Depends(get_okh_service)
):
    """
    Generate OKH manifest from repository URL
    
    Generates an OpenKnowHow manifest from a repository URL by analyzing
    the repository structure, metadata, and content. Supports GitHub and GitLab
    repositories with optional interactive review.
    
    The generation process includes:
    - URL validation and platform detection
    - Repository metadata extraction
    - Content analysis and field generation
    - Quality assessment and recommendations
    - Optional interactive review for field validation
    """
    try:
        # Call service to generate manifest from URL
        result = await okh_service.generate_from_url(
            url=request.url,
            skip_review=request.skip_review
        )
        
        return OKHGenerateResponse(**result)
        
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error generating manifest from URL {request.url}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the manifest"
        )


# Helper functions
async def _validate_okh_result(
    result: any,
    request_id: str
) -> List[ValidationResult]:
    """Validate OKH operation result."""
    try:
        validation_results = []
        
        # Basic validation
        is_valid = True
        errors = []
        warnings = []
        suggestions = []
        
        # Check if result exists
        if not result:
            is_valid = False
            errors.append("No result returned from operation")
        
        # Check required fields if result is a dict
        if isinstance(result, dict):
            if not result.get("id"):
                warnings.append("Missing ID in result")
            
            if not result.get("title"):
                warnings.append("Missing title in result")
        
        # Generate suggestions
        if not is_valid:
            suggestions.append("Review the input data and try again")
        
        validation_result = ValidationResult(
            is_valid=is_valid,
            score=1.0 if is_valid else 0.5,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
        
        validation_results.append(validation_result)
        
        return validation_results
        
    except Exception as e:
        logger.error(
            f"Error validating OKH result: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        return []