import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import yaml
from fastapi import (
    APIRouter,
    Body,
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
from fastapi.responses import Response


from ...services.cleanup_service import CleanupOptions, CleanupService
from ...services.asset_service import AssetService
from ...services.okh_service import OKHService
from ...services.scaffold_service import ScaffoldService
from ...services.storage_service import StorageService
from ...utils.logging import get_logger
from ..constants.client_errors import (
    ERROR_NO_FILE_PROVIDED,
    ERROR_UNSUPPORTED_YAML_JSON_FILE,
    format_invalid_file_format_detail,
)
from ..constants.openapi import RESPONSES_400_401_422_500
from ..decorators import (
    api_endpoint,
    paginated_response,
    track_performance,
)
from ..error_handlers import create_error_response

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
    OKHExtractRequest,
    OKHFromStorageRequest,
    OKHGenerateRequest,
    OKHHarvestRequest,
    OKHUpdateRequest,
    OKHValidateRequest,
)
from ..models.okh.response import (
    OKHExportResponse,
    OKHExtractResponse,
    OKHGenerateResponse,
    OKHHarvestResponse,
    OKHImportRepairDocResponse,
    OKHRepairExtractResponse,
    OKHResponse,
    OKHUploadResponse,
)
from ..models.scaffold.request import ScaffoldRequest

# Set up logging
logger = get_logger(__name__)

# Create router with standardized patterns
router = APIRouter(
    tags=["okh"],
    responses=RESPONSES_400_401_422_500,
)


# Service dependencies
async def get_okh_service() -> OKHService:
    """Get OKH service instance."""
    return await OKHService.get_instance()


async def get_asset_service() -> AssetService:
    return await AssetService.get_instance()


async def get_storage_service() -> StorageService:
    """Get storage service instance."""
    return await StorageService.get_instance()


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
async def export_okh_schema(http_request: Request = None) -> Any:
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


@router.get(
    "/template",
    summary="Get blank OKH manifest template",
    description="""
    Return a blank OKH manifest template as a JSON object.

    All fields are shown with their zero/empty/null defaults so the user can
    fill them in and then validate with ``POST /api/okh/validate``.
    """,
)
async def get_okh_template(http_request: Request = None) -> Any:
    """Return a blank OKH manifest template dict."""
    from ...utils.template_builder import okh_blank_template

    template = okh_blank_template()
    return {"success": True, "template": template, "model_name": "OKHManifest"}


@router.get(
    "/export-collection",
    summary="Export OKH collection as zip archive",
)
async def export_collection_endpoint(
    okh_service: OKHService = Depends(get_okh_service),
) -> Any:
    """Return all stored OKH manifests as a downloadable zip archive."""
    from ...packaging.collection import export_collection

    manifests, _ = await okh_service.list(page=1, page_size=10_000)
    if not manifests:
        raise HTTPException(
            status_code=404, detail="No OKH manifests found in collection"
        )

    archive_bytes = export_collection(manifests)
    return Response(
        content=archive_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=ohm-collection.zip"},
    )


@router.post(
    "/manifests/",
    response_model=OKHResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an OKH manifest",
    description="Create a new OKH manifest from a JSON body. Generates a UUID and persists to storage.",
)
async def create_okh_manifest(
    data: Dict[str, Any] = Body(...),
    okh_service: OKHService = Depends(get_okh_service),
) -> Any:
    try:
        manifest = await okh_service.create(data)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return OKHResponse.model_validate(
        {
            **manifest.to_dict(),
            "status": APIStatus.SUCCESS,
            "message": "OKH manifest created successfully",
        }
    )


@router.delete(
    "/manifests/{id}",
    response_model=SuccessResponse,
    summary="Delete an OKH manifest (path alias)",
)
async def delete_okh_manifest_alias(
    id: UUID = Path(...),
    okh_service: OKHService = Depends(get_okh_service),
) -> Any:
    """Alias for DELETE /{id} — used by integration test cleanup."""
    existing = await okh_service.get(id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OKH manifest with ID {id} not found",
        )
    success = await okh_service.delete(id)
    return SuccessResponse(success=success, message=f"OKH manifest {id} deleted")


@router.get("/{id}", response_model=OKHResponse)
async def get_okh(
    id: UUID = Path(..., title="The ID of the OKH manifest"),
    component: Optional[str] = Query(
        None, description="Specific component to retrieve"
    ),
    http_request: Request = None,
    okh_service: OKHService = Depends(get_okh_service),
) -> Any:
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
        # Use model_validate for more robust construction that handles type conversions
        response_data = {
            **manifest_dict,
            "status": APIStatus.SUCCESS,
            "message": "OKH manifest retrieved successfully",
            "request_id": request_id,
            "timestamp": datetime.now(),
        }

        # Use model_validate to handle any type conversions or extra fields gracefully
        return OKHResponse.model_validate(response_data)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Handle invalid parameters
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log unexpected errors with full traceback
        logger.error(
            f"Error retrieving OKH manifest {id}: {str(e)}",
            exc_info=True,
            extra={
                "request_id": request_id,
                "okh_id": str(id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
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
) -> Any:
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
) -> Any:
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
        return OKHResponse.model_validate(
            {
                **result.to_dict(),
                "status": APIStatus.SUCCESS,
                "message": "OKH manifest updated successfully",
            }
        )
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
) -> Any:
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
) -> Any:
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
) -> Any:
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
    "/create",
    response_model=OKHUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create OKH Manifest from JSON",
    description="""
    Create and store an OKH manifest from a JSON body.

    Accepts a manifest dictionary (e.g. collected via the interactive CLI wizard),
    validates it, and stores it. Returns the stored manifest id and metadata.
    """,
)
async def create_okh_manifest(
    request: OKHValidateRequest,
    okh_service: OKHService = Depends(get_okh_service),
    http_request: Request = None,
) -> Any:
    """Create and store an OKH manifest from a JSON dict."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )
    try:
        from ...models.okh import OKHManifest

        okh_manifest = OKHManifest.from_dict(request.content)
        try:
            okh_manifest.validate()
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"OKH validation failed: {str(e)}",
            )

        result = await okh_service.create(okh_manifest.to_dict())
        result_dict = result.to_dict()
        okh_response = OKHResponse(**result_dict)

        return OKHUploadResponse(
            success=True,
            message="OKH manifest created and stored successfully",
            manifest=okh_response,
            manifest_id=str(okh_manifest.id),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error creating OKH manifest: {str(e)}",
            extra={"request_id": request_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating OKH manifest: {str(e)}",
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
) -> Any:
    """
    Upload an OKH file

    Accepts a file upload (YAML or JSON) containing an OKH manifest,
    validates it, and stores it for use in matching operations.
    """
    try:
        # Validate file type
        if not okh_file.filename:
            raise HTTPException(status_code=400, detail=ERROR_NO_FILE_PROVIDED)

        file_extension = okh_file.filename.lower().split(".")[-1]
        if file_extension not in ["yaml", "yml", "json"]:
            raise HTTPException(
                status_code=400,
                detail=ERROR_UNSUPPORTED_YAML_JSON_FILE,
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
                status_code=400, detail=format_invalid_file_format_detail(e)
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
) -> Any:
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
) -> Any:
    """
    Generate OKH manifest from repository URL or local clone path

    Accepts either a remote repository URL (GitHub / GitLab) or an absolute path
    to an already-cloned local directory on the server filesystem.  Analyzes the
    repository structure, metadata, and content to produce an OKH manifest.

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
        # Call service to generate manifest from URL or local path
        result = await okh_service.generate_from_url(
            url=request.url,
            skip_review=request.skip_review,
            verbose=request.verbose,
            clone=request.clone,
            save_clone=request.save_clone,
            no_llm=request.no_llm,
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
) -> Any:
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
) -> Any:
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


# ---------------------------------------------------------------------------
# Collection import / export / diff  (#176)
# ---------------------------------------------------------------------------


@router.post(
    "/import-collection",
    summary="Import OKH manifests from a collection archive",
    response_model=dict,
)
async def import_collection_endpoint(
    file: UploadFile = File(
        ..., description="Collection zip archive produced by export-collection"
    ),
    dry_run: bool = Query(False, description="Analyse without writing"),
    okh_service: OKHService = Depends(get_okh_service),
    http_request: Request = None,
) -> Any:
    """Classify and optionally import manifests from a collection archive."""
    from ...packaging.collection import analyse_import

    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )
    archive_bytes = await file.read()

    try:
        local_manifests, _ = await okh_service.list(page=1, page_size=10_000)
        report, incoming = analyse_import(archive_bytes, local_manifests)

        imported = 0
        if not dry_run:
            for manifest in incoming.values():
                await okh_service.create(manifest)
                imported += 1

        return {
            "status": "success",
            "request_id": request_id,
            "dry_run": dry_run,
            "new": report.new,
            "duplicate": report.duplicate,
            "conflict": report.conflict,
            "imported": imported,
        }
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Ensure the archive was produced by 'ohm okh export-collection'",
        )
        logger.error(f"Error importing collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post(
    "/diff-collection",
    summary="Diff an archive against the local OKH collection",
    response_model=dict,
)
async def diff_collection_endpoint(
    file: UploadFile = File(..., description="Collection zip archive to compare"),
    okh_service: OKHService = Depends(get_okh_service),
    http_request: Request = None,
) -> Any:
    """Return the symmetric diff between an archive and the local collection."""
    from ...packaging.collection import diff_collection

    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )
    archive_bytes = await file.read()

    try:
        local_manifests, _ = await okh_service.list(page=1, page_size=10_000)
        diff = diff_collection(archive_bytes, local_manifests)
        return {
            "status": "success",
            "request_id": request_id,
            "only_in_archive": diff["only_in_archive"],
            "only_local": diff["only_local"],
        }
    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Ensure the archive was produced by 'ohm okh export-collection'",
        )
        logger.error(f"Error diffing collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post(
    "/extract-repair-docs",
    response_model=OKHRepairExtractResponse,
    summary="Extract repair fields from uploaded documents",
    description="""
    Upload one or more repair documents (PDF, service manuals, parts catalogs, etc.)
    and extract structured OKH repair fields: components with part numbers, repair
    guides with tools and safety prerequisites, diagnostic codes, and document type.

    **Pass 1 (always runs)**: programmatic heuristics — works fully offline.
    **Pass 2 (optional)**: LLM enrichment — set `use_llm=true` and ensure an LLM
    provider is configured to enable this pass.

    If `manifest_id` is provided, the extracted fields are merged into that manifest
    and the manifest's new state is reflected in the response.
    """,
)
async def extract_repair_docs(
    files: list[UploadFile] = File(..., description="Repair documents to analyse"),
    manifest_id: Optional[str] = Form(None, description="Merge into this manifest"),
    use_llm: bool = Form(False, description="Run optional LLM enrichment pass"),
    okh_service: OKHService = Depends(get_okh_service),
) -> Any:
    """Extract repair-specific OKH fields from uploaded documents."""
    import tempfile
    from pathlib import Path as FsPath
    from uuid import UUID as UUIDType

    from ...generation.repair_doc_extractor import RepairDocExtractor

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file must be provided.",
        )

    try:
        # Write uploads to a temp directory so the extractor can read them
        extractor = RepairDocExtractor()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_paths: list[FsPath] = []
            for upload in files:
                dest = FsPath(tmp_dir) / (upload.filename or "document")
                dest.write_bytes(await upload.read())
                tmp_paths.append(dest)

            if use_llm:
                try:
                    from ...llm.service import LLMService, LLMServiceConfig

                    llm_cfg = LLMServiceConfig()
                    llm_svc = LLMService("RepairExtract", llm_cfg)
                    result = await extractor.extract_with_llm(tmp_paths, llm_svc)
                except Exception as llm_err:
                    logger.warning(
                        f"LLM init failed for repair extraction; falling back to "
                        f"programmatic: {llm_err}"
                    )
                    result = extractor.extract(tmp_paths)
            else:
                result = extractor.extract(tmp_paths)

        merged_manifest_id: Optional[str] = None
        if manifest_id:
            try:
                existing = await okh_service.get(UUIDType(manifest_id))
                if existing is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Manifest {manifest_id!r} not found.",
                    )
                patch = result.to_patch()
                existing_dict = existing.to_dict()
                existing_dict["components"] = existing_dict.get(
                    "components", []
                ) + patch.get("components", [])
                existing_dict["repair_guides"] = existing_dict.get(
                    "repair_guides", []
                ) + patch.get("repair_guides", [])
                await okh_service.update(UUIDType(manifest_id), existing_dict)
                merged_manifest_id = manifest_id
            except HTTPException:
                raise
            except Exception as merge_err:
                logger.error(
                    f"Failed to merge into manifest {manifest_id}: {merge_err}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Extraction succeeded but manifest merge failed: {merge_err}",
                )

        return OKHRepairExtractResponse(
            success=True,
            message=(
                f"Extracted repair fields from {len(result.source_files)} file(s)"
                + (" with LLM enhancement" if result.llm_enhanced else "")
            ),
            components=[c.to_dict() for c in result.components],
            repair_guides=[g.to_dict() for g in result.repair_guides],
            documentation_type=(
                result.documentation_type.value if result.documentation_type else None
            ),
            source_files=result.source_files,
            llm_enhanced=result.llm_enhanced,
            notes=result.notes,
            manifest_id=merged_manifest_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in extract-repair-docs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during repair document extraction.",
        )


_ANNOTATION_REMINDER = (
    "New components have been imported with replaceable=False and salvageable=False. "
    "Annotate these flags in the manifest before using it for triage or salvage matching."
)


@router.post(
    "/import-repair-doc",
    response_model=OKHImportRepairDocResponse,
    status_code=status.HTTP_200_OK,
    summary="Import repair documents into an OKH manifest with conservative defaults",
    description="""
    Extract repair fields from one or more uploaded documents and merge them into an
    OKH manifest, or create a new manifest from the extraction output.

    **Merge semantics** (distinct from `/extract-repair-docs`):
    - Components already in the manifest keep their existing `replaceable` and
      `salvageable` flags.
    - Newly-extracted components are imported with `replaceable=False` and
      `salvageable=False` regardless of what the extractor inferred.  A human must
      annotate these flags before the manifest can drive triage or salvage matching.
    - Deduplication is by component name (case-insensitive).
    - Repair guides are deduplicated by title.

    **Create mode** (`manifest_id` omitted): set `title` to name the new manifest.
    **Patch mode** (`manifest_id` provided): merges into the named manifest.
    """,
)
async def import_repair_doc(
    files: list[UploadFile] = File(..., description="Repair documents to analyse"),
    manifest_id: Optional[str] = Form(None, description="Patch this manifest"),
    title: Optional[str] = Form(None, description="Title for a new manifest"),
    use_llm: bool = Form(False, description="Run optional LLM enrichment pass"),
    okh_service: OKHService = Depends(get_okh_service),
) -> Any:
    import tempfile
    from pathlib import Path as FsPath
    from uuid import UUID as UUIDType

    from ...generation.repair_doc_extractor import RepairDocExtractor

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file must be provided.",
        )
    if manifest_id is None and not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either manifest_id (to patch) or title (to create).",
        )

    try:
        extractor = RepairDocExtractor()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_paths: list[FsPath] = []
            for upload in files:
                dest = FsPath(tmp_dir) / (upload.filename or "document")
                dest.write_bytes(await upload.read())
                tmp_paths.append(dest)

            if use_llm:
                try:
                    from ...llm.service import LLMService, LLMServiceConfig

                    llm_svc = LLMService("ImportRepairDoc", LLMServiceConfig())
                    result = await extractor.extract_with_llm(tmp_paths, llm_svc)
                except Exception as llm_err:
                    logger.warning(
                        f"LLM init failed; falling back to programmatic: {llm_err}"
                    )
                    result = extractor.extract(tmp_paths)
            else:
                result = extractor.extract(tmp_paths)

        # Count before to report what changed
        mid_uuid = UUIDType(manifest_id) if manifest_id else None
        if mid_uuid:
            pre = await okh_service.get(mid_uuid)
            pre_comp_names = (
                {c.name.lower() for c in (pre.components or [])} if pre else set()
            )
            pre_guide_titles = (
                {g.title.lower() for g in (pre.repair_guides or [])} if pre else set()
            )
        else:
            pre_comp_names = set()
            pre_guide_titles = set()

        manifest = await okh_service.import_repair_doc(
            result, manifest_id=mid_uuid, title=title
        )

        new_comp_names = {c.name.lower() for c in (manifest.components or [])}
        added = len(new_comp_names - pre_comp_names)
        updated = len(
            new_comp_names
            & pre_comp_names
            & {c.name.lower() for c in result.components}
        )
        new_guide_titles = {g.title.lower() for g in (manifest.repair_guides or [])}
        guides_added = len(new_guide_titles - pre_guide_titles)

        action = "merged into" if mid_uuid else "created"
        return OKHImportRepairDocResponse(
            success=True,
            message=(
                f"Imported {len(result.source_files)} file(s) — {action} manifest {manifest.id}"
                + (" with LLM enhancement" if result.llm_enhanced else "")
            ),
            manifest_id=str(manifest.id),
            components_added=added,
            components_updated=updated,
            guides_added=guides_added,
            source_files=result.source_files,
            llm_enhanced=result.llm_enhanced,
            notes=result.notes,
            annotation_reminder=_ANNOTATION_REMINDER,
        )

    except HTTPException:
        raise
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in import-repair-doc: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during repair document import.",
        )


@router.post(
    "/harvest-parts",
    response_model=OKHHarvestResponse,
    summary="Harvest components from one or more manifests",
    description="""
    Given one or more manifest IDs, return a flat inventory of their components,
    each annotated with the source manifest ID and title.

    Use the filter flags to narrow results to components that are specifically
    relevant for repair or parts reuse:
    - **replaceable_only** — components the designer marked as field-replaceable
    - **salvageable_only** — components that can be harvested for use elsewhere
    - **consumable_only** — periodic-replacement items (filters, seals, fuses, …)
    - **has_part_number** — components with a manufacturer/supplier part number
    """,
)
async def harvest_parts(
    request: OKHHarvestRequest,
    okh_service: OKHService = Depends(get_okh_service),
    asset_service: AssetService = Depends(get_asset_service),
) -> Any:
    """Return a flat component inventory harvested from the requested manifests."""
    from uuid import UUID as UUIDType

    components: list[dict] = []
    found_ids: list[str] = []

    for mid in request.manifest_ids:
        try:
            manifest = await okh_service.get(UUIDType(mid))
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid manifest ID: {mid!r}",
            )
        if manifest is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manifest {mid!r} not found.",
            )

        found_ids.append(mid)
        title = getattr(manifest, "title", None) or mid

        for component in manifest.components:
            c = component.to_dict()
            if request.replaceable_only and not c.get("replaceable"):
                continue
            if request.salvageable_only and not c.get("salvageable"):
                continue
            if request.consumable_only and not c.get("consumable"):
                continue
            if request.has_part_number and not c.get("part_number"):
                continue
            c["source_manifest_id"] = mid
            c["source_manifest_title"] = title
            components.append(c)

    if request.enrich_fleet:
        for c in components:
            result = await asset_service.salvage_match(component_name=c["name"])
            c["fleet_available_count"] = len(result.matches)
            c["fleet_asset_ids"] = [m.asset_id for m in result.matches]

    return OKHHarvestResponse(
        components=components,
        total=len(components),
        replaceable_count=sum(1 for c in components if c.get("replaceable")),
        consumable_count=sum(1 for c in components if c.get("consumable")),
        salvageable_count=sum(1 for c in components if c.get("salvageable")),
        source_manifests=found_ids,
    )
