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
from pydantic import Field

from ...models.okw import ManufacturingFacility
from ...services.okw_service import OKWService
from ...services.storage_service import StorageService
from ...utils.logging import get_logger
from ..decorators import (
    api_endpoint,
    llm_endpoint,
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
from ..models.okw.request import (
    OKWCreateRequest,
    OKWExtractRequest,
    OKWUpdateRequest,
    OKWValidateRequest,
)
from ..models.okw.response import (
    Capability,
    OKWExportResponse,
    OKWExtractResponse,
    OKWListResponse,
    OKWResponse,
    OKWUploadResponse,
)

# Set up logging
logger = get_logger(__name__)

# Create router with standardized patterns
router = APIRouter(
    tags=["okw"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"},
    },
)


# Service dependencies
async def get_storage_service() -> StorageService:
    """Get storage service instance."""
    return await StorageService.get_instance()


async def get_okw_service() -> OKWService:
    """Get OKW service instance."""
    return await OKWService.get_instance()


@router.post(
    "/create",
    response_model=OKWResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create OKW Facility",
    description="""
    Create a new OpenKnowWhere facility with enhanced capabilities.
    
    This endpoint provides:
    - Standardized request/response formats
    - LLM integration support
    - Enhanced error handling
    - Performance metrics
    - Validation
    
    **Features:**
    - Support for LLM-enhanced facility creation
    - Advanced validation options
    - Real-time performance tracking
    - Detailed validation results
    """,
)
@validate_request(OKWCreateRequest)
@track_performance("okw_creation")
# @llm_endpoint(
#     default_provider="anthropic",
#     default_model="claude-sonnet-4-5",
#     track_costs=True
# )
async def create_okw(
    request: OKWCreateRequest,
    http_request: Request,
    okw_service: OKWService = Depends(get_okw_service),
):
    """
    Enhanced OKW facility creation with standardized patterns.

    Args:
        request: Enhanced OKW create request with standardized fields
        http_request: HTTP request object for tracking
        okw_service: OKW service dependency

    Returns:
        Enhanced OKW response with data
    """
    request_id = getattr(http_request.state, "request_id", None)
    start_time = datetime.now()

    try:
        # Convert request to facility data
        facility_data = request.model_dump(mode="json")

        # Create facility using service
        facility = await okw_service.create(facility_data)

        # Convert to response format
        location_dict = (
            facility.location.to_dict()
            if hasattr(facility.location, "to_dict")
            else {
                "address": (
                    facility.location.address.to_dict()
                    if hasattr(facility.location.address, "to_dict")
                    else {
                        "street": getattr(facility.location.address, "street", ""),
                        "city": getattr(facility.location.address, "city", ""),
                        "region": getattr(facility.location.address, "region", ""),
                        "postal_code": getattr(
                            facility.location.address, "postal_code", ""
                        ),
                        "country": getattr(facility.location.address, "country", ""),
                    }
                ),
                "coordinates": {
                    "latitude": getattr(facility.location, "latitude", None),
                    "longitude": getattr(facility.location, "longitude", None),
                },
            }
        )

        # Convert enum values to strings
        facility_status_str = (
            facility.facility_status.value
            if hasattr(facility.facility_status, "value")
            else str(facility.facility_status)
        )
        access_type_str = (
            facility.access_type.value
            if hasattr(facility.access_type, "value")
            else str(facility.access_type)
        )

        facility_dict = {
            "id": str(facility.id),
            "name": facility.name,
            "location": location_dict,
            "facility_status": facility_status_str,
            "access_type": access_type_str,
            "manufacturing_processes": (
                list(facility.manufacturing_processes)
                if facility.manufacturing_processes
                else []
            ),
            "equipment": (
                [eq.to_dict() for eq in facility.equipment]
                if facility.equipment
                else []
            ),
            "typical_materials": (
                [mat.to_dict() for mat in facility.typical_materials]
                if facility.typical_materials
                else []
            ),
        }

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        # Create enhanced response matching OKWResponse structure
        from ...models.base import APIStatus
        
        response_data = {
            **facility_dict,  # Include all facility fields directly
            "status": APIStatus.SUCCESS,
            "message": "OKW facility created successfully",
            "timestamp": datetime.now(),
            "request_id": request_id,
            "processing_time": processing_time,
            "validation_results": await _validate_okw_result(facility_dict, request_id),
        }

        logger.info(
            f"OKW facility created successfully",
            extra={
                "request_id": request_id,
                "facility_id": str(facility.id),
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
            f"Validation error creating OKW facility: {str(e)}",
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
            f"Error creating OKW facility: {str(e)}",
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


@router.get("/search", response_model=OKWListResponse)
async def search_okw(
    location: Optional[str] = Query(
        None, description="Geographic location to search near"
    ),
    capabilities: Optional[List[str]] = Query(
        None, description="Required capabilities"
    ),
    materials: Optional[List[str]] = Query(None, description="Required materials"),
    access_type: Optional[str] = Query(None, description="Access type filter"),
    facility_status: Optional[str] = Query(None, description="Facility status filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Search for facilities by criteria"""
    try:
        # Load OKW facilities from storage (same logic as matching route)
        facilities = []
        try:
            # Get all objects from storage (these are the actual OKW files)
            objects = []
            async for obj in storage_service.manager.list_objects():
                objects.append(obj)

            logger.info(f"Found {len(objects)} objects in storage")

            # Load and parse each OKW file
            for obj in objects:
                try:
                    # Read the file content
                    data = await storage_service.manager.get_object(obj["key"])
                    content = data.decode("utf-8")

                    # Parse based on file extension
                    if obj["key"].endswith((".yaml", ".yml")):
                        okw_data = yaml.safe_load(content)
                    elif obj["key"].endswith(".json"):
                        okw_data = json.loads(content)
                    else:
                        logger.warning(
                            f"Skipping unsupported file format: {obj['key']}"
                        )
                        continue

                    # Create ManufacturingFacility object
                    facility = ManufacturingFacility.from_dict(okw_data)
                    facilities.append(facility)
                    logger.debug(
                        f"Loaded OKW facility from {obj['key']}: {facility.name}"
                    )

                except Exception as e:
                    logger.error(f"Failed to load OKW facility from {obj['key']}: {e}")
                    continue

            logger.info(f"Loaded {len(facilities)} OKW facilities from storage.")
        except Exception as e:
            logger.error(f"Failed to list/load OKW facilities: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to load OKW facilities: {str(e)}"
            )

        # Apply search filters
        filtered_facilities = []
        logger.info(
            f"Applying filters: access_type='{access_type}', facility_status='{facility_status}', location='{location}'"
        )

        for facility in facilities:
            logger.debug(
                f"Checking facility: {facility.name} (access_type: {facility.access_type})"
            )

            # Location filter
            if location and location.lower() not in str(facility.location).lower():
                logger.debug(f"  Filtered out by location: {facility.name}")
                continue

            # Capabilities filter
            if capabilities:
                facility_capabilities = [
                    cap.get("name", "").lower() for cap in facility.equipment
                ]
                if not any(
                    cap.lower() in facility_capabilities for cap in capabilities
                ):
                    logger.debug(f"  Filtered out by capabilities: {facility.name}")
                    continue

            # Materials filter
            if materials:
                facility_materials = [mat.lower() for mat in facility.typical_materials]
                if not any(mat.lower() in facility_materials for mat in materials):
                    logger.debug(f"  Filtered out by materials: {facility.name}")
                    continue

            # Access type filter
            if access_type:
                facility_access_type = facility.access_type.value.lower()
                filter_access_type = access_type.lower()
                logger.debug(
                    f"  Comparing access_type: '{facility_access_type}' vs '{filter_access_type}'"
                )
                if facility_access_type != filter_access_type:
                    logger.debug(f"  Filtered out by access_type: {facility.name}")
                    continue

            # Facility status filter
            if (
                facility_status
                and facility.facility_status.value.lower() != facility_status.lower()
            ):
                logger.debug(f"  Filtered out by facility_status: {facility.name}")
                continue

            logger.debug(f"  Facility passed all filters: {facility.name}")
            filtered_facilities.append(facility)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_facilities = filtered_facilities[start_idx:end_idx]

        # Convert to response format
        results = []
        for facility in paginated_facilities:
            # Convert Location object to dict for serialization
            location_dict = (
                facility.location.to_dict()
                if hasattr(facility.location, "to_dict")
                else {
                    "address": (
                        facility.location.address.to_dict()
                        if hasattr(facility.location.address, "to_dict")
                        else {
                            "street": getattr(facility.location.address, "street", ""),
                            "city": getattr(facility.location.address, "city", ""),
                            "region": getattr(facility.location.address, "region", ""),
                            "postal_code": getattr(
                                facility.location.address, "postal_code", ""
                            ),
                            "country": getattr(
                                facility.location.address, "country", ""
                            ),
                        }
                    ),
                    "coordinates": {
                        "latitude": getattr(facility.location, "latitude", None),
                        "longitude": getattr(facility.location, "longitude", None),
                    },
                }
            )

            # Convert facility_status and access_type to strings if they're enums
            facility_status_str = (
                facility.facility_status.value
                if hasattr(facility.facility_status, "value")
                else str(facility.facility_status)
            )
            access_type_str = (
                facility.access_type.value
                if hasattr(facility.access_type, "value")
                else str(facility.access_type)
            )

            # Create OKWResponse object with all required fields
            okw_response = OKWResponse(
                status=APIStatus.SUCCESS,
                message="OKW facility retrieved successfully",
                id=facility.id,
                name=facility.name,
                location=location_dict,
                facility_status=facility_status_str,
                access_type=access_type_str,
                manufacturing_processes=facility.manufacturing_processes or [],
                equipment=(
                    [
                        eq.to_dict() if hasattr(eq, "to_dict") else eq
                        for eq in facility.equipment
                    ]
                    if facility.equipment
                    else []
                ),
                typical_materials=(
                    [
                        mat.to_dict() if hasattr(mat, "to_dict") else mat
                        for mat in facility.typical_materials
                    ]
                    if facility.typical_materials
                    else []
                ),
                owner=(
                    facility.owner.to_dict()
                    if facility.owner and hasattr(facility.owner, "to_dict")
                    else None
                ),
                contact=(
                    facility.contact.to_dict()
                    if facility.contact and hasattr(facility.contact, "to_dict")
                    else None
                ),
                description=facility.description,
                opening_hours=facility.opening_hours,
                date_founded=(
                    facility.date_founded.isoformat() if facility.date_founded else None
                ),
                wheelchair_accessibility=facility.wheelchair_accessibility,
                typical_batch_size=(
                    str(facility.typical_batch_size)
                    if facility.typical_batch_size
                    else None
                ),
                floor_size=facility.floor_size,
                storage_capacity=facility.storage_capacity,
                certifications=facility.certifications or [],
                domain=facility.domain,
            )

            results.append(okw_response)

        return OKWListResponse(
            results=results,
            total=len(filtered_facilities),
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Error searching OKW facilities: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error searching OKW facilities: {str(e)}"
        )


@router.get(
    "/schema",
    response_model=OKWExportResponse,
    summary="Get OKW JSON Schema",
    description="""
    Get the JSON schema for the OKW (OpenKnowWhere) domain model in canonical format.
    
    This endpoint generates a JSON schema that represents the complete structure
    of the ManufacturingFacility dataclass, including all fields, types, and constraints.
    
    **Features:**
    - Canonical JSON Schema format (draft-07)
    - Complete type definitions
    - Required field specifications
    - Nested object schemas
    """,
)
@router.get(
    "/export",
    response_model=OKWExportResponse,
    summary="Export OKW JSON Schema",
    description="""
    Export the JSON schema for the OKW (OpenKnowWhere) domain model in canonical format.
    
    This endpoint generates a JSON schema that represents the complete structure
    of the ManufacturingFacility dataclass, including all fields, types, and constraints.
    
    **Features:**
    - Canonical JSON Schema format (draft-07)
    - Complete type definitions
    - Required field specifications
    - Nested object schemas
    """,
)
async def export_okw_schema(http_request: Request = None):
    """Export OKW domain model as JSON schema."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        from ...models.okw import ManufacturingFacility
        from ...utils.schema_generator import generate_json_schema

        # Generate JSON schema from ManufacturingFacility dataclass
        schema = generate_json_schema(
            ManufacturingFacility, title="ManufacturingFacility"
        )

        logger.info(
            "OKW schema exported successfully",
            extra={
                "request_id": request_id,
                "schema_title": schema.get("title"),
                "schema_version": schema.get("$schema"),
            },
        )

        return OKWExportResponse(
            success=True,
            message="OKW schema exported successfully",
            json_schema=schema,
            schema_version=schema.get(
                "$schema", "http://json-schema.org/draft-07/schema#"
            ),
            model_name="ManufacturingFacility",
        )

    except Exception as e:
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error exporting OKW schema: {str(e)}",
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


@router.get("/{id}", response_model=OKWResponse)
async def get_okw(
    id: UUID = Path(..., title="The ID of the OKW facility"),
    okw_service: OKWService = Depends(get_okw_service),
):
    """Get an OKW facility by ID"""
    try:
        facility = await okw_service.get(id)
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKW facility with ID {id} not found",
            )

        # Convert to response format
        location_dict = (
            facility.location.to_dict()
            if hasattr(facility.location, "to_dict")
            else {
                "address": (
                    facility.location.address.to_dict()
                    if hasattr(facility.location.address, "to_dict")
                    else {
                        "street": getattr(facility.location.address, "street", ""),
                        "city": getattr(facility.location.address, "city", ""),
                        "region": getattr(facility.location.address, "region", ""),
                        "postal_code": getattr(
                            facility.location.address, "postal_code", ""
                        ),
                        "country": getattr(facility.location.address, "country", ""),
                    }
                ),
                "coordinates": {
                    "latitude": getattr(facility.location, "latitude", None),
                    "longitude": getattr(facility.location, "longitude", None),
                },
            }
        )

        # Convert facility_status and access_type to strings if they're enums
        facility_status_str = (
            facility.facility_status.value
            if hasattr(facility.facility_status, "value")
            else str(facility.facility_status)
        )
        access_type_str = (
            facility.access_type.value
            if hasattr(facility.access_type, "value")
            else str(facility.access_type)
        )

        # Return OKWResponse with fields at top level (not nested in data)
        return OKWResponse(
            status=APIStatus.SUCCESS,
            message="OKW facility retrieved successfully",
            id=facility.id,
            name=facility.name,
            location=location_dict,
            facility_status=facility_status_str,
            access_type=access_type_str,
            manufacturing_processes=facility.manufacturing_processes or [],
            equipment=(
                [
                    eq.to_dict() if hasattr(eq, "to_dict") else eq
                    for eq in facility.equipment
                ]
                if facility.equipment
                else []
            ),
            typical_materials=(
                [
                    mat.to_dict() if hasattr(mat, "to_dict") else mat
                    for mat in facility.typical_materials
                ]
                if facility.typical_materials
                else []
            ),
            owner=(
                facility.owner.to_dict()
                if facility.owner and hasattr(facility.owner, "to_dict")
                else None
            ),
            contact=(
                facility.contact.to_dict()
                if facility.contact and hasattr(facility.contact, "to_dict")
                else None
            ),
            description=facility.description,
            opening_hours=facility.opening_hours,
            date_founded=(
                facility.date_founded.isoformat() if facility.date_founded else None
            ),
            wheelchair_accessibility=facility.wheelchair_accessibility,
            typical_batch_size=(
                str(facility.typical_batch_size)
                if facility.typical_batch_size
                else None
            ),
            floor_size=facility.floor_size,
            storage_capacity=facility.storage_capacity,
            certifications=facility.certifications or [],
            domain=facility.domain,  # Include domain field
            request_id=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting OKW facility {id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error getting OKW facility: {str(e)}"
        )


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List OKW Facilities",
    description="""
    Get a paginated list of OpenKnowWhere facilities with enhanced capabilities.
    
    **Features:**
    - Paginated results with sorting and filtering
    - Enhanced error handling
    - Performance metrics
    - validation
    """,
)
@paginated_response(default_page_size=20, max_page_size=100)
async def list_okw(
    pagination: PaginationParams = Depends(),
    filter: Optional[str] = Query(None, description="Filter criteria"),
    okw_service: OKWService = Depends(get_okw_service),
    http_request: Request = None,
):
    """Enhanced OKW facility listing with pagination and metrics."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Call service to list OKW facilities
        facilities, total = await okw_service.list(
            pagination.page, pagination.page_size, None
        )

        # Convert ManufacturingFacility objects to dict format
        results = []
        for facility in facilities:
            # Convert Location object to dict for serialization
            location_dict = (
                facility.location.to_dict()
                if hasattr(facility.location, "to_dict")
                else {
                    "address": (
                        facility.location.address.to_dict()
                        if hasattr(facility.location.address, "to_dict")
                        else {
                            "street": getattr(facility.location.address, "street", ""),
                            "city": getattr(facility.location.address, "city", ""),
                            "region": getattr(facility.location.address, "region", ""),
                            "postal_code": getattr(
                                facility.location.address, "postal_code", ""
                            ),
                            "country": getattr(
                                facility.location.address, "country", ""
                            ),
                        }
                    ),
                    "coordinates": {
                        "latitude": getattr(facility.location, "latitude", None),
                        "longitude": getattr(facility.location, "longitude", None),
                    },
                }
            )

            facility_dict = {
                "id": str(facility.id),
                "name": facility.name,
                "location": location_dict,
                "facility_status": facility.facility_status,
                "access_type": facility.access_type,
                "manufacturing_processes": facility.manufacturing_processes,
                "equipment": facility.equipment,
                "typical_materials": facility.typical_materials,
            }
            results.append(facility_dict)

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
            message="OKW facilities listed successfully",
            pagination=pagination_info,
            items=results,
            request_id=request_id,
        )

    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists",
        )
        logger.error(
            f"Error listing OKW facilities: {str(e)}",
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


@router.put("/{id}", response_model=OKWResponse)
async def update_okw(
    request: OKWUpdateRequest,
    id: UUID = Path(..., title="The ID of the OKW facility"),
    okw_service: OKWService = Depends(get_okw_service),
):
    """Update an OKW facility"""
    try:
        # Check if facility exists
        existing_facility = await okw_service.get(id)
        if not existing_facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKW facility with ID {id} not found",
            )

        # Convert request to facility data
        facility_data = request.dict()
        facility_data["id"] = str(id)  # Ensure ID is preserved

        # Update facility using service
        facility = await okw_service.update(id, facility_data)

        # Convert to response format
        location_dict = (
            facility.location.to_dict()
            if hasattr(facility.location, "to_dict")
            else {
                "address": (
                    facility.location.address.to_dict()
                    if hasattr(facility.location.address, "to_dict")
                    else {
                        "street": getattr(facility.location.address, "street", ""),
                        "city": getattr(facility.location.address, "city", ""),
                        "region": getattr(facility.location.address, "region", ""),
                        "postal_code": getattr(
                            facility.location.address, "postal_code", ""
                        ),
                        "country": getattr(facility.location.address, "country", ""),
                    }
                ),
                "coordinates": {
                    "latitude": getattr(facility.location, "latitude", None),
                    "longitude": getattr(facility.location, "longitude", None),
                },
            }
        )

        return {
            "id": str(facility.id),
            "name": facility.name,
            "location": location_dict,
            "facility_status": facility.facility_status,
            "access_type": facility.access_type,
            "manufacturing_processes": facility.manufacturing_processes,
            "equipment": (
                [eq.to_dict() for eq in facility.equipment]
                if facility.equipment
                else []
            ),
            "typical_materials": (
                [mat.to_dict() for mat in facility.typical_materials]
                if facility.typical_materials
                else []
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating OKW facility {id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error updating OKW facility: {str(e)}"
        )


@router.delete("/{id}", response_model=SuccessResponse)
async def delete_okw(
    id: UUID = Path(..., title="The ID of the OKW facility"),
    okw_service: OKWService = Depends(get_okw_service),
):
    """Delete an OKW facility"""
    try:
        # Check if facility exists
        existing_facility = await okw_service.get(id)
        if not existing_facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"OKW facility with ID {id} not found",
            )

        # Delete facility using service
        success = await okw_service.delete(id)

        if success:
            return SuccessResponse(
                success=True, message=f"OKW facility with ID {id} deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete OKW facility with ID {id}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting OKW facility {id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error deleting OKW facility: {str(e)}"
        )


@router.post(
    "/validate",
    response_model=ValidationResult,
    summary="Validate OKW Facility",
    description="""
    Validate an OKW facility with domain-aware validation and enhanced capabilities.
    
    Validates an OpenKnowWhere facility against domain-specific validation rules
    based on the specified quality level. The validation framework provides:
    
    - **Hobby Level**: Relaxed validation for makerspaces and hobby facilities
    - **Professional Level**: Standard validation for commercial manufacturing facilities  
    - **Medical Level**: Strict validation for medical device manufacturing facilities
    
    Returns detailed validation results including errors, warnings, and
    completeness scoring.
    """,
)
@track_performance("okw_validation")
async def validate_okw(
    request: OKWValidateRequest,
    quality_level: Optional[str] = Query(
        "professional", description="Quality level: hobby, professional, or medical"
    ),
    strict_mode: Optional[bool] = Query(
        False, description="Enable strict validation mode"
    ),
    okw_service: OKWService = Depends(get_okw_service),
    http_request: Request = None,
):
    """Enhanced OKW validation with standardized patterns."""
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )

    try:
        # Use quality_level from query parameter, fallback to validation_context
        validation_context = (
            quality_level or request.validation_context or "professional"
        )

        logger.info(
            "Validating OKW facility",
            extra={
                "validation_context": validation_context,
                "strict_mode": strict_mode,
                "request_id": request_id,
            },
        )

        # Use common validation utility that validates against canonical ManufacturingFacility dataclass
        from ...validation.model_validator import validate_okw_facility

        validation_result = validate_okw_facility(
            content=request.content,
            quality_level=validation_context,
            strict_mode=strict_mode,
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
            f"Validation error in OKW validation: {str(e)}",
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
            f"Error validating OKW facility: {str(e)}",
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


@router.post("/extract", response_model=OKWExtractResponse)
@track_performance("okw_extract_capabilities")
async def extract_capabilities(
    request: OKWExtractRequest, http_request: Request = None
):
    """
    Extract capabilities from an OKW object.

    This endpoint extracts manufacturing capabilities from OKW facility data
    using the domain-specific extractor. The extracted capabilities can be
    used for matching against OKH requirements.

    Args:
        request: OKW extract request containing facility data
        http_request: HTTP request object

    Returns:
        OKWExtractResponse with extracted capabilities

    Raises:
        HTTPException: If extraction fails or data is invalid
    """
    request_id = (
        getattr(http_request.state, "request_id", None) if http_request else None
    )
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
                extra={"request_id": request_id},
            )
            return OKWExtractResponse(capabilities=[])

        # Extract capabilities from normalized data
        normalized_capabilities = extraction_result.data
        capabilities_list = []

        # Convert NormalizedCapabilities to List[Capability]
        # The content field contains the capabilities
        if hasattr(normalized_capabilities, "content"):
            content = normalized_capabilities.content

            # Extract capabilities array
            if isinstance(content, dict):
                capabilities_data = content.get("capabilities", [])

                # Convert to Capability objects
                for cap_data in capabilities_data:
                    if isinstance(cap_data, dict):
                        # Capability model only has type, parameters, limitations (no name field)
                        capability = Capability(
                            type=cap_data.get(
                                "process_name",
                                cap_data.get("name", cap_data.get("type", "process")),
                            ),
                            parameters=cap_data.get("parameters", {}),
                            limitations=cap_data.get("limitations", {}),
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
                "processing_time": processing_time,
            },
        )

        return OKWExtractResponse(capabilities=capabilities_list)

    except ValueError as e:
        # Invalid domain or extractor not found
        error_response = create_error_response(
            error=f"Invalid domain or extractor not available: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
            request_id=request_id,
            suggestion="Please check the domain configuration",
        )
        logger.error(
            f"Extraction failed: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response.model_dump(mode="json"),
        )

    except Exception as e:
        # Generic error handling
        error_response = create_error_response(
            error=f"Failed to extract capabilities: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please check the OKW content format and try again",
        )
        logger.error(
            f"Extraction error: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode="json"),
        )


@router.post(
    "/upload", response_model=OKWUploadResponse, status_code=status.HTTP_201_CREATED
)
async def upload_okw_file(
    okw_file: UploadFile = File(..., description="OKW file (YAML or JSON)"),
    description: Optional[str] = Form(
        None, description="Optional description for the uploaded OKW"
    ),
    tags: Optional[str] = Form(None, description="Comma-separated list of tags"),
    validation_context: Optional[str] = Form(
        None, description="Validation context (e.g., 'manufacturing', 'hobby')"
    ),
    okw_service: OKWService = Depends(get_okw_service),
):
    """
    Upload an OKW file

    Accepts a file upload (YAML or JSON) containing an OKW facility,
    validates it, and stores it for use in matching operations.
    """
    try:
        # Validate file type
        if not okw_file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        file_extension = okw_file.filename.lower().split(".")[-1]
        if file_extension not in ["yaml", "yml", "json"]:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload a YAML (.yaml, .yml) or JSON (.json) file",
            )

        # Read and parse the file content
        content = await okw_file.read()
        content_str = content.decode("utf-8")

        try:
            if file_extension == "json":
                okw_data = json.loads(content_str)
            else:  # yaml or yml
                okw_data = yaml.safe_load(content_str)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid file format: {str(e)}"
            )

        # Convert to ManufacturingFacility
        try:
            okw_facility = ManufacturingFacility.from_dict(okw_data)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid OKW facility: {str(e)}"
            )

        # Store the OKW facility
        try:
            result = await okw_service.create(okw_facility.to_dict())
        except Exception as e:
            logger.error(f"Error storing OKW facility: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error storing OKW facility: {str(e)}"
            )

        # Convert result to OKWResponse format (result is a ManufacturingFacility object)
        location_dict = (
            result.location.to_dict()
            if hasattr(result.location, "to_dict")
            else (
                {
                    "address": (
                        result.location.address.to_dict()
                        if hasattr(result.location.address, "to_dict")
                        else {
                            "street": getattr(result.location.address, "street", ""),
                            "city": getattr(result.location.address, "city", ""),
                            "country": getattr(result.location.address, "country", ""),
                        }
                    )
                }
                if result.location
                else {}
            )
        )

        facility_status_str = (
            result.facility_status.value
            if hasattr(result.facility_status, "value")
            else str(result.facility_status)
        )
        access_type_str = (
            result.access_type.value
            if hasattr(result.access_type, "value")
            else str(result.access_type)
        )

        okw_response = OKWResponse(
            status=APIStatus.SUCCESS,
            message="OKW facility uploaded successfully",
            id=result.id,
            name=result.name,
            location=location_dict,
            facility_status=facility_status_str,
            access_type=access_type_str,
            equipment=(
                [
                    eq.to_dict() if hasattr(eq, "to_dict") else eq
                    for eq in result.equipment
                ]
                if result.equipment
                else []
            ),
            typical_materials=(
                [
                    mat.to_dict() if hasattr(mat, "to_dict") else mat
                    for mat in result.typical_materials
                ]
                if result.typical_materials
                else []
            ),
            owner=(
                result.owner.to_dict()
                if result.owner and hasattr(result.owner, "to_dict")
                else None
            ),
            contact=(
                result.contact.to_dict()
                if result.contact and hasattr(result.contact, "to_dict")
                else None
            ),
            description=result.description,
            opening_hours=result.opening_hours,
            date_founded=(
                result.date_founded.isoformat() if result.date_founded else None
            ),
            wheelchair_accessibility=result.wheelchair_accessibility,
            typical_batch_size=(
                str(result.typical_batch_size) if result.typical_batch_size else None
            ),
            floor_size=result.floor_size,
            storage_capacity=result.storage_capacity,
            certifications=result.certifications or [],
            request_id=None,
        )

        return OKWUploadResponse(
            success=True,
            message=f"OKW file '{okw_file.filename}' uploaded and stored successfully",
            okw=okw_response,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading OKW file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Helper functions
async def _validate_okw_result(result: any, request_id: str) -> List[ValidationResult]:
    """Validate OKW operation result."""
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

            if not result.get("name"):
                warnings.append("Missing name in result")

            if not result.get("location"):
                warnings.append("Missing location in result")

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
            f"Error validating OKW result: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        return []
