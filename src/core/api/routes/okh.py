import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import yaml
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.encoders import jsonable_encoder
from pydantic import Field

from src.config import settings

from ...services.cleanup_service import CleanupOptions, CleanupService
from ...services.okh_service import OKHService
from ...services.scaffold_service import ScaffoldService
from ...services.storage_service import StorageService
from ...utils.logging import get_logger
from ..decorators import (
    api_endpoint,
    paginated_response,
    track_performance,
    validate_request,
)
from ..error_handlers import create_error_response, create_success_response

# Import new standardized components
from ..models.base import (
    APIStatus,
    PaginatedResponse,
    PaginationInfo,
    PaginationParams,
    SuccessResponse,
    ValidationResult,
)
from ..models.cleanup.request import CleanupRequest
from ..models.cleanup.response import CleanupResponse

# Import existing models and services (now properly used through inheritance)
from ..models.okh.request import (
    OKHCreateRequest,
    OKHExtractRequest,
    OKHFromStorageRequest,
    OKHGenerateRequest,
    OKHUpdateRequest,
    OKHValidateRequest,
)
from ..models.okh.response import (
    OKHExportResponse,
    OKHExtractResponse,
    OKHGenerateResponse,
    OKHResponse,
    OKHUploadResponse,
)
from ..models.scaffold.request import ScaffoldRequest
from ..models.scaffold.response import ScaffoldResponse

# Set up logging
logger = get_logger(__name__)

# Create router with standardized patterns
router = APIRouter(
    tags=["okh"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)


# Service dependencies
async def get_okh_service() -> OKHService:
    """Get OKH service instance."""
    return await OKHService.get_instance()


async def get_storage_service() -> StorageService:
    """Get storage service instance."""
    return await StorageService.get_instance()


@router.post(
    "/create",
    response_model=OKHResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create OKH Manifest",
    description="""
    Create a new OpenKnowHow manifest with enhanced capabilities.
    
    This endpoint provides:
    - Standardized request/response formats
    - LLM integration support
    - Enhanced error handling
    - Performance metrics
    - Validation
    
    **Features:**
    - Support for LLM-enhanced manifest creation
    - Advanced validation options
    - Real-time performance tracking
    - Detailed validation results
    """,
)
@validate_request(OKHCreateRequest)
@track_performance("okh_creation")
# @llm_endpoint(
#     default_provider="anthropic",
#     default_model="claude-sonnet-4-5",
#     track_costs=True
# )
async def create_okh(
    request: OKHCreateRequest,
    http_request: Request,
    okh_service: OKHService = Depends(get_okh_service),
):
    """
    Enhanced OKH manifest creation with standardized patterns.

    Args:
        request: Enhanced OKH create request with standardized fields
        http_request: HTTP request object for tracking
        okh_service: OKH service dependency

    Returns:
        Enhanced OKH response with data
    """
    request_id = getattr(http_request.state, "request_id", None)
    start_time = datetime.now()

    try:
        # Call service to create OKH manifest
        result = await okh_service.create(request.model_dump(mode="json"))

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Create enhanced response using the proper OKHResponse structure
        from ...models.base import APIStatus

        result_dict = result.to_dict() if hasattr(result, "to_dict") else result
        response_data = {
            **result_dict,  # Include all OKHResponse fields
            "status": APIStatus.SUCCESS,
            "message": "OKH manifest created successfully",
            "timestamp": datetime.now(),
            "request_id": request_id,
            "processing_time": processing_time,
            "validation_results": await _validate_okh_result(result, request_id),
        }

        logger.info(
            f"OKH manifest created successfully",
            extra={
                "request_id": request_id,
                "processing_time": processing_time,
                "llm_used": request.use_llm,
            },
        )

        return response_data

    except ValueError as e:
        # Handle validation errors using standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id=request_id,
            suggestion="Please check the input data and try again",
        )
        logger.error(
            f"Validation error creating OKH manifest: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        # Log unexpected errors using standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error creating OKH manifest: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get(
    "/export",
    response_model=OKHExportResponse,
    summary="Export OKH JSON Schema",
    description="""
    Export the JSON schema for the OKH (OpenKnowHow) domain model in canonical format.
    
    This endpoint generates a JSON schema that represents the complete structure
    of the OKHManifest dataclass, including all fields, types, and constraints.
    
    **Features:**
    - Canonical JSON Schema format (draft-07)
    - Complete type definitions
    - Required field specifications
    - Nested object schemas
    """,
)
async def export_okh_schema(http_request: Request = None):
    """Export OKH domain model as JSON schema."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        from ...models.okh import OKHManifest
        from ...utils.schema_generator import generate_json_schema

        # Generate JSON schema from OKHManifest dataclass
        schema = generate_json_schema(OKHManifest, title="OKHManifest")

        logger.info(
            "OKH schema exported successfully",
            extra={
                "request_id": request_id,
                "schema_title": schema.get("title"),
                "schema_version": schema.get("$schema"),
            },
        )

        return OKHExportResponse(
            success=True,
            message="OKH schema exported successfully",
            json_schema=schema,
            schema_version=schema.get(
                "$schema", "http://json-schema.org/draft-07/schema#"
            ),
            model_name="OKHManifest",
        )

    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error exporting OKH schema: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.get("/{id}", response_model=OKHResponse)
async def get_okh(
    id: UUID = Path(..., title="The ID of the OKH manifest"),
    component: Optional[str] = Query(
        None, description="Specific component to retrieve"
    ),
    http_request: Request = None,
    okh_service: OKHService = Depends(get_okh_service),
):
    """
    Get an OKH manifest by ID

    Retrieves a specific OpenKnowHow manifest by its unique identifier.
    Optionally retrieves only a specific component of the manifest.
    """
    try:
        # Get request ID if available
        request_id = (
            getattr(http_request.state, "request_id", None) if http_request else None
        )

        # Call service to get OKH manifest
        result = await okh_service.get(id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKH manifest with ID {id} not found",
            )

        # Convert OKHManifest to dict
        manifest_dict = result.to_dict()

        # Construct OKHResponse with required SuccessResponse fields
        return OKHResponse(
            status=APIStatus.SUCCESS,
            message="OKH manifest retrieved successfully",
            request_id=request_id,
            **manifest_dict,
        )
    except ValueError as e:
        # Handle invalid parameters
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error retrieving OKH manifest {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the OKH manifest",
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
    - Validation
    """,
)
@paginated_response(default_page_size=20, max_page_size=100)
async def list_okh(
    http_request: Request,
    pagination: PaginationParams = Depends(),
    filter: Optional[str] = Query(
        None, description="Filter criteria (e.g., 'title=contains:Hardware')"
    ),
    okh_service: OKHService = Depends(get_okh_service),
):
    """Enhanced OKH manifest listing with pagination and metrics."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Parse filter parameter if provided
        filter_params = {}
        if filter:
            # Simple parsing for filter format: field=operator:value
            # For example: title=contains:Hardware
            parts = filter.split("=", 1)
            if len(parts) == 2:
                field, op_value = parts
                op_parts = op_value.split(":", 1)
                if len(op_parts) == 2:
                    op, value = op_parts
                    filter_params = {"field": field, "operator": op, "value": value}

        # Call service to list OKH manifests
        manifests, total = await okh_service.list(
            pagination.page, pagination.page_size, filter_params
        )

        # Convert OKHManifest objects to dict format
        results = []
        for manifest in manifests:
            # Convert OKHManifest to dict
            manifest_dict = (
                manifest.to_dict() if hasattr(manifest, "to_dict") else manifest
            )
            results.append(manifest_dict)

        # Create pagination info
        total_pages = (total + pagination.page_size - 1) // pagination.page_size

        # Create proper PaginatedResponse
        pagination_info = PaginationInfo(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        )

        return PaginatedResponse(
            status=APIStatus.SUCCESS,
            message="OKH manifests listed successfully",
            pagination=pagination_info,
            items=results,
            request_id=request_id,
        )

    except ValueError as e:
        # Handle invalid parameters
        logger.error(
            f"Invalid parameters for OKH listing: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error listing OKH manifests: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.put("/{id}", response_model=OKHResponse)
async def update_okh(
    request: OKHUpdateRequest,
    id: UUID = Path(..., title="The ID of the OKH manifest"),
    okh_service: OKHService = Depends(get_okh_service),
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
                detail=f"OKH manifest with ID {id} not found",
            )

        # Call service to update OKH manifest
        result = await okh_service.update(id, request.model_dump(mode="json"))
        return result
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error updating OKH manifest {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the OKH manifest",
        )


@router.delete("/{id}", response_model=SuccessResponse)
async def delete_okh(
    id: UUID = Path(..., title="The ID of the OKH manifest"),
    okh_service: OKHService = Depends(get_okh_service),
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
                detail=f"OKH manifest with ID {id} not found",
            )

        # Call service to delete OKH manifest
        success = await okh_service.delete(id)

        return SuccessResponse(
            success=success, message=f"OKH manifest with ID {id} deleted successfully"
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error deleting OKH manifest {id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the OKH manifest",
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
    """,
)
@track_performance("okh_validation")
async def validate_okh(
    request: OKHValidateRequest,
    quality_level: Optional[str] = Query(
        "professional", description="Quality level: hobby, professional, or medical"
    ),
    strict_mode: Optional[bool] = Query(
        False, description="Enable strict validation mode"
    ),
    okh_service: OKHService = Depends(get_okh_service),
    http_request: Request = None,
):
    """Enhanced OKH validation with standardized patterns."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Use quality_level from query parameter, fallback to validation_context
        validation_context = (
            quality_level or request.validation_context or "professional"
        )

        logger.info(
            "Validating OKH manifest",
            extra={
                "validation_context": validation_context,
                "strict_mode": strict_mode,
                "request_id": request_id,
            },
        )

        # Use common validation utility that validates against canonical OKHManifest dataclass
        from ...validation.model_validator import validate_okh_manifest

        # Detect domain from request content or use default
        domain = None
        if isinstance(request.content, dict):
            domain = request.content.get("domain")

        validation_result = validate_okh_manifest(
            content=request.content,
            quality_level=validation_context,
            strict_mode=strict_mode,
            domain=domain,
        )

        # Convert to API ValidationResult format
        api_result = validation_result.to_api_format()
        api_result["metadata"]["request_id"] = request_id

        return ValidationResult(**api_result)

    except ValueError as e:
        # Handle validation errors using standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id=request_id,
            suggestion="Please check the validation parameters and try again",
        )
        logger.error(
            f"Validation error in OKH validation: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        # Log unexpected errors using standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error validating OKH manifest: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post("/extract", response_model=OKHExtractResponse)
async def extract_requirements(
    request: OKHExtractRequest, okh_service: OKHService = Depends(get_okh_service)
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error extracting requirements: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while extracting requirements",
        )


@router.post(
    "/upload", response_model=OKHUploadResponse, status_code=status.HTTP_201_CREATED
)
async def upload_okh_file(
    okh_file: UploadFile = File(..., description="OKH file (YAML or JSON)"),
    description: Optional[str] = Form(
        None, description="Optional description for the uploaded OKH"
    ),
    tags: Optional[str] = Form(None, description="Comma-separated list of tags"),
    validation_context: Optional[str] = Form(
        None, description="Validation context (e.g., 'manufacturing', 'hobby')"
    ),
    okh_service: OKHService = Depends(get_okh_service),
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

        file_extension = okh_file.filename.lower().split(".")[-1]
        if file_extension not in ["yaml", "yml", "json"]:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload a YAML (.yaml, .yml) or JSON (.json) file",
            )

        # Read and parse the file content
        content = await okh_file.read()
        content_str = content.decode("utf-8")

        try:
            if file_extension == "json":
                okh_data = json.loads(content_str)
            else:  # yaml or yml
                okh_data = yaml.safe_load(content_str)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid file format: {str(e)}"
            )

        # Convert to OKHManifest
        try:
            from ...models.okh import OKHManifest

            okh_manifest = OKHManifest.from_dict(okh_data)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid OKH manifest: {str(e)}"
            )

        # Validate the manifest
        try:
            okh_manifest.validate()
        except ValueError as e:
            raise HTTPException(
                status_code=400, detail=f"OKH validation failed: {str(e)}"
            )

        # Store the OKH manifest
        try:
            result = await okh_service.create(okh_manifest.to_dict())
        except Exception as e:
            logger.error(f"Error storing OKH manifest: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error storing OKH manifest: {str(e)}"
            )

        # Convert result to OKHResponse format
        result_dict = result.to_dict()
        okh_response = OKHResponse(**result_dict)

        return OKHUploadResponse(
            success=True,
            message=f"OKH file '{okh_file.filename}' uploaded and stored successfully",
            okh=okh_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading OKH file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/from-storage",
    response_model=OKHResponse,
    summary="Get OKH from Storage",
    description="""
    Retrieve an OKH manifest from storage by ID.
    
    This endpoint retrieves a previously stored OKH manifest from the storage service
    using its unique identifier.
    """,
)
@api_endpoint(
    success_message="OKH manifest retrieved from storage successfully",
    include_metrics=True,
)
@track_performance("okh_from_storage")
async def get_okh_from_storage(
    request: OKHFromStorageRequest,
    http_request: Request = None,
    okh_service: OKHService = Depends(get_okh_service),
):
    """Retrieve an OKH manifest from storage by ID."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Parse manifest_id as UUID
        try:
            manifest_id = UUID(request.manifest_id)
        except ValueError:
            error_response = create_error_response(
                error=f"Invalid manifest ID format: {request.manifest_id}",
                status_code=status.HTTP_400_BAD_REQUEST,
                request_id=request_id,
                suggestion="Please provide a valid UUID for the manifest ID",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.model_dump(mode="json"),
            )

        # Get manifest from storage
        manifest = await okh_service.get(manifest_id)

        if not manifest:
            error_response = create_error_response(
                error=f"OKH manifest with ID {manifest_id} not found in storage",
                status_code=status.HTTP_404_NOT_FOUND,
                request_id=request_id,
                suggestion="Please check the manifest ID and try again",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_response.model_dump(mode="json"),
            )

        # Convert OKHManifest to OKHResponse
        manifest_dict = manifest.to_dict()

        logger.info(
            f"OKH manifest retrieved from storage successfully",
            extra={
                "request_id": request_id,
                "manifest_id": str(manifest_id),
                "title": manifest.title,
            },
        )

        return OKHResponse(**manifest_dict)

    except HTTPException:
        raise
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error retrieving OKH manifest from storage: {str(e)}",
            extra={
                "request_id": request_id,
                "manifest_id": request.manifest_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post("/generate-from-url", response_model=OKHGenerateResponse)
async def generate_from_url(
    request: OKHGenerateRequest, okh_service: OKHService = Depends(get_okh_service)
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
    - **Intelligent file categorization** using two-layer approach:
      - **Layer 1 (Heuristics)**: Fast rule-based categorization using file extensions,
        directory paths, and filename patterns
      - **Layer 2 (LLM)**: Content-aware categorization with semantic understanding
        (when LLM is available, falls back to Layer 1 if unavailable)
    - Files are categorized into:
      - `making_instructions`: Step-by-step assembly/build guides for humans
      - `manufacturing_files`: Machine-readable files (.stl, .3mf, .gcode, etc.)
      - `design_files`: Source CAD files (.scad, .fcstd, etc.)
      - `operating_instructions`: User manuals and usage guides
      - `technical_specifications`: Technical specs, dimensions, validation reports
      - `publications`: Research papers and academic publications
      - `documentation_home`: Main project documentation (README.md)
    - Quality assessment and recommendations
    - Optional interactive review for field validation
    """
    try:
        # Call service to generate manifest from URL
        result = await okh_service.generate_from_url(
            url=request.url, skip_review=request.skip_review, verbose=request.verbose
        )

        return OKHGenerateResponse(**result)

    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error generating manifest from URL {request.url}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the manifest",
        )


@router.post(
    "/scaffold",
    summary="Generate OKH project scaffold",
    description="Create an OKH-compliant project structure with documentation stubs and manifest template.",
)
async def scaffold_project(
    request: ScaffoldRequest,
    http_request: Request,
    okh_service: OKHService = Depends(
        get_okh_service
    ),  # kept for parity; not used directly here
    scaffold_service: "ScaffoldService" = Depends(
        lambda: __import__(
            "src.core.services.scaffold_service", fromlist=["ScaffoldService"]
        ).ScaffoldService()
    ),
):
    """Generate a scaffold using ScaffoldService and return structured response."""
    from src.core.services.scaffold_service import ScaffoldOptions

    request_id = getattr(http_request.state, "request_id", None)

    try:
        options = ScaffoldOptions(
            project_name=request.project_name,
            version=request.version,
            organization=request.organization,
            template_level=request.template_level,  # type: ignore
            output_format=request.output_format,  # type: ignore
            output_path=request.output_path,
            include_examples=request.include_examples,
            okh_version=request.okh_version,
        )

        result = await scaffold_service.generate_scaffold(options)

        # Return response as dict with timestamp explicitly converted to ISO string
        # (Manually construct dict to avoid any serializer recursion issues)
        try:
            response_dict = {
                "status": "success",
                "message": "Scaffold generated successfully",
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
                "project_name": result.project_name,
                "structure": result.structure,
                "manifest_template": result.manifest_template,
                "download_url": result.download_url,
                "filesystem_path": result.filesystem_path,
            }
            # Use jsonable_encoder to ensure all nested datetime objects are converted
            encoded_response = jsonable_encoder(response_dict)
            return encoded_response
        except Exception as e:
            # Log the exact error for debugging
            logger.error(f"Error serializing scaffold response: {e}", exc_info=True)
            raise
    except ValueError as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            request_id=request_id,
            suggestion="Please check the scaffold request parameters and try again",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_response.model_dump(mode="json"),
        )
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error generating scaffold: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post(
    "/scaffold/cleanup",
    summary="Clean and optimize an OKH project directory",
    response_model=CleanupResponse,
    description="Remove unmodified documentation stubs and empty directories from a scaffolded project.",
)
async def cleanup_project(
    request: CleanupRequest,
    http_request: Request,
    cleanup_service: "CleanupService" = Depends(
        lambda: __import__(
            "src.core.services.cleanup_service", fromlist=["CleanupService"]
        ).CleanupService()
    ),
):
    request_id = getattr(http_request.state, "request_id", None)

    try:
        options = CleanupOptions(
            project_path=request.project_path,
            remove_unmodified_stubs=request.remove_unmodified_stubs,
            remove_empty_directories=request.remove_empty_directories,
            dry_run=request.dry_run,
        )

        result = await cleanup_service.clean(options)

        return {
            "status": "success",
            "message": (
                "Cleanup completed" if not request.dry_run else "Dry run completed"
            ),
            "request_id": request_id,
            "removed_files": result.removed_files,
            "removed_directories": result.removed_directories,
            "bytes_saved": result.bytes_saved,
            "warnings": result.warnings,
        }
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please verify the project_path and try again",
        )
        logger.error(
            f"Error during scaffold cleanup: {str(e)}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


# Helper functions
async def _validate_okh_result(result: any, request_id: str) -> List[ValidationResult]:
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
            suggestions=suggestions,
        )

        validation_results.append(validation_result)

        return validation_results

    except Exception as e:
        logger.error(
            f"Error validating OKH result: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        return []
