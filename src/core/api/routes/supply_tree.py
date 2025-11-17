from fastapi import APIRouter, HTTPException, Query, Path, status, Request, Depends, Body, Response
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import json

from ..models.base import (
    BaseAPIRequest, 
    SuccessResponse, 
    ErrorResponse,
    PaginationParams,
    PaginatedResponse,
    LLMRequestMixin,
    LLMResponseMixin,
    ValidationResult as BaseValidationResult
)
from ..decorators import (
    api_endpoint,
    validate_request,
    track_performance,
    llm_endpoint,
    paginated_response
)
from ..error_handlers import create_error_response, create_success_response
from ..models.supply_tree.request import (
    SupplyTreeCreateRequest,
    SupplyTreeValidateRequest,
    SupplyTreeOptimizeRequest
)
from ..models.supply_tree.response import (
    SupplyTreeResponse,
    ValidationResult
)
from ...utils.logging import get_logger
from ...services.storage_service import StorageService
from ...services.okh_service import OKHService
from ...services.okw_service import OKWService
from ...models.supply_trees import SupplyTree
from ...models.okh import OKHManifest
from ...models.okw import ManufacturingFacility

logger = get_logger(__name__)

# Dependency functions
async def get_storage_service() -> StorageService:
    """Get storage service instance."""
    from ....config import settings
    storage_service = await StorageService.get_instance()
    
    # Configure storage service if not already configured
    if not storage_service._configured:
        try:
            await storage_service.configure(settings.STORAGE_CONFIG)
        except Exception as e:
            logger.warning(f"Failed to configure storage service: {e}")
            # Return service anyway - it will handle errors in methods
    
    return storage_service


async def get_okh_service() -> OKHService:
    """Get OKH service instance."""
    return await OKHService.get_instance()


async def get_okw_service() -> OKWService:
    """Get OKW service instance."""
    return await OKWService.get_instance()

# Create router with standardized patterns
router = APIRouter(
    prefix="/api/supply-tree",
    tags=["supply-tree"],
    responses={
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        422: {"description": "Validation Error"},
        500: {"description": "Internal Server Error"}
    }
)

# Note: Enhanced models have been consolidated into the base models in request.py and response.py

@router.post(
    "/create", 
    # Note: response_model removed - api_endpoint decorator handles response wrapping
    status_code=status.HTTP_201_CREATED,
    summary="Create Supply Tree",
    description="""
    Create a supply tree with enhanced capabilities.
    
    This endpoint provides:
    - Standardized request/response formats
    - LLM integration support
    - Enhanced error handling
    - Performance metrics
    - Validation
    
    **Features:**
    - Support for LLM-enhanced supply tree creation
    - Advanced workflow definitions
    - Real-time performance tracking
    - Detailed validation results
    """
)
@api_endpoint(
    success_message="Supply tree created successfully",
    include_metrics=True,
    track_llm=True
)
@validate_request(SupplyTreeCreateRequest)
@track_performance("supply_tree_create")
@llm_endpoint(
    default_provider="anthropic",
    default_model="claude-sonnet-4-5",
    track_costs=True
)
async def create_supply_tree(
    request: SupplyTreeCreateRequest,
    http_request: Request,
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service),
    okw_service: OKWService = Depends(get_okw_service)
):
    """
    Enhanced supply tree creation with standardized patterns.
    
    Args:
        create_request: Enhanced supply tree creation request with standardized fields
        http_request: HTTP request object for tracking
        
    Returns:
        Enhanced supply tree response with data
    """
    request_id = getattr(http_request.state, 'request_id', None)
    start_time = datetime.now()
    
    try:
        # Get the facility and OKH manifest for creating the supply tree
        facility = await okw_service.get(request.facility_id)
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Facility with ID {request.facility_id} not found"
            )
        
        # Try to get OKH manifest if okh_reference is a UUID, otherwise use as reference
        okh_manifest = None
        if request.okh_reference:
            try:
                okh_manifest = await okh_service.get(UUID(request.okh_reference))
            except (ValueError, TypeError):
                # If okh_reference is not a valid UUID, treat it as a reference string
                # Try to find it by searching storage or skip OKH manifest loading
                pass
        
        # Create the supply tree
        if okh_manifest:
            # Use factory method if manifest is available
            supply_tree = SupplyTree.from_facility_and_manifest(
                facility=facility,
                manifest=okh_manifest,
                confidence_score=request.confidence_score,
                match_type=request.match_type,
                estimated_cost=request.estimated_cost,
                estimated_time=request.estimated_time
            )
            
            # Override with request-specific data
            supply_tree.materials_required = request.materials_required
            supply_tree.capabilities_used = request.capabilities_used
            supply_tree.metadata.update(request.metadata)
        else:
            # Create supply tree directly from request data when manifest is not available
            supply_tree = SupplyTree(
                facility_name=request.facility_name or facility.name,
                okh_reference=request.okh_reference,
                confidence_score=request.confidence_score,
                okw_reference=str(facility.id),
                match_type=request.match_type,
                estimated_cost=request.estimated_cost,
                estimated_time=request.estimated_time,
                materials_required=request.materials_required or [],
                capabilities_used=request.capabilities_used or [],
                metadata=request.metadata or {}
            )
        
        # Save the supply tree to storage
        if storage_service:
            await storage_service.save_supply_tree(supply_tree)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Convert okw_reference to facility_id for response
        # SupplyTree uses okw_reference (string), but response expects facility_id (UUID)
        facility_id = facility.id
        if supply_tree.okw_reference:
            try:
                facility_id = UUID(supply_tree.okw_reference)
            except (ValueError, TypeError):
                # If okw_reference is not a valid UUID, use facility.id
                facility_id = facility.id
        
        # Create response data using the consolidated model structure
        response_data = {
            "id": supply_tree.id,
            "facility_id": facility_id,
            "facility_name": supply_tree.facility_name,
            "okh_reference": supply_tree.okh_reference,
            "confidence_score": supply_tree.confidence_score,
            "creation_time": supply_tree.creation_time.isoformat(),
            "estimated_cost": supply_tree.estimated_cost,
            "estimated_time": supply_tree.estimated_time,
            "materials_required": supply_tree.materials_required,
            "capabilities_used": supply_tree.capabilities_used,
            "match_type": supply_tree.match_type,
            "metadata": supply_tree.metadata,
            "processing_time": processing_time,
            "validation_results": await _validate_supply_tree_result(supply_tree.to_dict(), request_id)
        }
        
        logger.info(
            f"Supply tree created successfully",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(supply_tree.id),
                "facility_id": str(facility_id),
                "okh_reference": supply_tree.okh_reference,
                "confidence_score": supply_tree.confidence_score,
                "processing_time": processing_time,
                "llm_used": getattr(request, 'use_llm', False)
            }
        )
        
        return response_data
        
    except Exception as e:
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error creating supply tree: {str(e)}",
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

@router.get(
    "/{id}", 
    # Note: response_model removed - api_endpoint decorator handles response wrapping
    summary="Get Supply Tree",
    description="Get a specific supply tree by ID with enhanced capabilities."
)
@api_endpoint(
    success_message="Supply tree retrieved successfully",
    include_metrics=True
)
@track_performance("supply_tree_get")
async def get_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service)
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
        
        try:
            supply_tree = await storage_service.load_supply_tree(id)
        except FileNotFoundError as e:
            # Tree doesn't exist - return 404
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
        # Note: SupplyTree model doesn't have a direct facility_id field.
        # We attempt to derive it from metadata or okw_reference.
        # If unavailable, we use None (which is acceptable for the response model).
        facility_id = None
        if supply_tree.metadata and "facility_id" in supply_tree.metadata:
            try:
                facility_id = UUID(supply_tree.metadata["facility_id"])
            except (ValueError, TypeError):
                pass
        
        # If still no facility_id, try to parse from okw_reference if it's a UUID
        if not facility_id and supply_tree.okw_reference:
            try:
                facility_id = UUID(supply_tree.okw_reference)
            except (ValueError, TypeError):
                pass
        
        # If still no facility_id, use the standard nil UUID (all-zeros) as a sentinel value
        # Note: Response model requires UUID (not Optional), so we use the standard nil UUID
        # (00000000-0000-0000-0000-000000000000) which is the standard way to represent "no UUID"
        # Clients can check for this value to detect when facility_id is not available
        if not facility_id:
            facility_id = UUID("00000000-0000-0000-0000-000000000000")
        
        response_data = {
            "id": str(supply_tree.id),
            "facility_id": str(facility_id),
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
        
        return response_data
        
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
        logger.error(
            f"Error getting supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )

@router.get(
    "", 
    response_model=PaginatedResponse,
    summary="List Supply Trees",
    description="""
    Get a paginated list of supply trees with enhanced capabilities.
    
    **Features:**
    - Paginated results with sorting and filtering
    - Enhanced error handling
    - Performance metrics
    - Validation
    """
)
@api_endpoint(
    success_message="Supply trees listed successfully",
    include_metrics=True
)
@paginated_response(default_page_size=20, max_page_size=100)
async def list_supply_trees(
    pagination: PaginationParams = Depends(),
    filter: Optional[str] = Query(None, description="Filter criteria"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Enhanced supply tree listing with pagination and metrics."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Check storage service availability
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available"
            )
        
        # List supply trees from storage (pagination handled by StorageService)
        try:
            supply_tree_list = await storage_service.list_supply_trees(
                limit=pagination.page_size,
                offset=(pagination.page - 1) * pagination.page_size
            )
        except RuntimeError as e:
            # Storage service not configured
            if "not configured" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Storage service not configured"
                )
            raise
        except Exception as e:
            # Handle other storage errors (e.g., connection issues, permission errors)
            logger.error(
                f"Error listing supply trees from storage: {str(e)}",
                extra={"request_id": request_id, "error": str(e)},
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Storage service error: {str(e)}"
            )
        
        # Convert to response format
        # StorageService returns list of dicts with: id, okh_reference, last_modified
        # We need to convert to items with more fields
        results = []
        for tree_info in supply_tree_list:
            if isinstance(tree_info, dict):
                # Create item from available metadata
                item = {
                    "id": tree_info.get("id"),
                    "okh_reference": tree_info.get("okh_reference")
                }
                
                # Convert last_modified to ISO format string if it's a datetime
                last_modified = tree_info.get("last_modified")
                if last_modified is not None:
                    if isinstance(last_modified, datetime):
                        item["last_modified"] = last_modified.isoformat()
                    else:
                        item["last_modified"] = str(last_modified)
                
                # Add optional fields if available
                if "facility_name" in tree_info:
                    item["facility_name"] = tree_info["facility_name"]
                if "confidence_score" in tree_info:
                    item["confidence_score"] = tree_info["confidence_score"]
                if "match_type" in tree_info:
                    item["match_type"] = tree_info["match_type"]
                if "creation_time" in tree_info:
                    creation_time = tree_info["creation_time"]
                    if isinstance(creation_time, datetime):
                        item["creation_time"] = creation_time.isoformat()
                    else:
                        item["creation_time"] = str(creation_time)
                elif "last_modified" in tree_info:
                    # Use last_modified as creation_time if available
                    creation_time = tree_info["last_modified"]
                    if isinstance(creation_time, datetime):
                        item["creation_time"] = creation_time.isoformat()
                    else:
                        item["creation_time"] = str(creation_time)
                
                results.append(item)
        
        # Return list for paginated_response decorator to handle
        # The decorator will wrap this in a PaginatedResponse
        return results
        
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
        logger.error(
            f"Error listing supply trees: {str(e)}",
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

@router.put(
    "/{id}",
    summary="Update Supply Tree",
    description="Update an existing supply tree with enhanced capabilities."
)
# @api_endpoint(
#     success_message="Supply tree updated successfully",
#     include_metrics=True
# )
# @track_performance("supply_tree_update")
async def update_supply_tree(
    request: SupplyTreeCreateRequest,
    id: UUID = Path(..., title="The ID of the supply tree"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service),
    okw_service: OKWService = Depends(get_okw_service)
):
    """Enhanced supply tree update with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    start_time = datetime.now()
    
    try:
        # Check storage service availability
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available"
            )
        
        # Load existing supply tree
        try:
            existing_tree = await storage_service.load_supply_tree(id)
        except Exception as e:
            # If load fails, tree doesn't exist
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
        logger.info(f"Update request received: facility_name={request.facility_name}, facility_id={request.facility_id}")
        logger.info(f"Existing tree before update: facility_name={existing_tree.facility_name}")
        
        # Update facility_name if provided (do this first so it takes precedence)
        if request.facility_name:
            existing_tree.facility_name = request.facility_name
            logger.info(f"Updated facility_name to: {request.facility_name}")
        
        # Update facility if facility_id is provided
        if request.facility_id:
            facility = await okw_service.get(request.facility_id)
            if facility:
                # Update facility-related fields from the facility
                existing_tree.okw_reference = str(facility.id)
                # Only update facility_name from facility if it wasn't explicitly provided in request
                if not request.facility_name:
                    existing_tree.facility_name = facility.name
            else:
                logger.info(f"Facility {request.facility_id} not found, skipping facility update")
        
        logger.info(f"Existing tree after update: facility_name={existing_tree.facility_name}")
        
        # Update OKH reference if provided
        if request.okh_reference:
            existing_tree.okh_reference = request.okh_reference
            # Try to load OKH manifest if it's a UUID
            try:
                okh_manifest = await okh_service.get(UUID(request.okh_reference))
                if okh_manifest:
                    # Update any OKH-related fields if needed
                    pass
            except (ValueError, TypeError):
                # If okh_reference is not a valid UUID, treat it as a reference string
                pass
        
        # Update other fields if provided
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
        logger.info(f"Saved tree with facility_name: {existing_tree.facility_name}")
        
        # Reload tree to ensure we have the latest version
        existing_tree = await storage_service.load_supply_tree(id)
        logger.info(f"Reloaded tree with facility_name: {existing_tree.facility_name}")
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Convert okw_reference to facility_id for response
        facility_id = None
        if existing_tree.okw_reference:
            try:
                facility_id = UUID(existing_tree.okw_reference)
            except (ValueError, TypeError):
                # If okw_reference is not a valid UUID, try to get facility from service
                if request and request.facility_id:
                    facility_id = request.facility_id
                else:
                    # Use a default UUID if we can't determine facility_id
                    facility_id = UUID("00000000-0000-0000-0000-000000000000")
        elif request and request.facility_id:
            facility_id = request.facility_id
        else:
            # Use a default UUID if we can't determine facility_id
            facility_id = UUID("00000000-0000-0000-0000-000000000000")
        
        # Create response data using the same format as create endpoint
        response_data = {
            "id": str(existing_tree.id),
            "facility_id": str(facility_id),
            "facility_name": existing_tree.facility_name,
            "okh_reference": existing_tree.okh_reference,
            "confidence_score": existing_tree.confidence_score,
            "creation_time": existing_tree.creation_time.isoformat(),
            "estimated_cost": existing_tree.estimated_cost,
            "estimated_time": existing_tree.estimated_time,
            "materials_required": existing_tree.materials_required,
            "capabilities_used": existing_tree.capabilities_used,
            "match_type": existing_tree.match_type,
            "metadata": existing_tree.metadata
        }
        
        logger.info(
            f"Supply tree updated successfully",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(existing_tree.id),
                "facility_id": str(facility_id),
                "okh_reference": existing_tree.okh_reference,
                "processing_time": processing_time
            }
        )
        
        return response_data
        
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
        logger.error(
            f"Error updating supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )

@router.delete(
    "/{id}", 
    response_model=SuccessResponse,
    summary="Delete Supply Tree",
    description="Delete a supply tree with enhanced capabilities."
)
@api_endpoint(
    success_message="Supply tree deleted successfully",
    include_metrics=True
)
@track_performance("supply_tree_delete")
async def delete_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Enhanced supply tree deletion with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Check storage service availability
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available"
            )
        
        # Check if supply tree exists
        try:
            existing_tree = await storage_service.load_supply_tree(id)
        except Exception as e:
            # If load fails, tree doesn't exist
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
        try:
            deleted = await storage_service.delete_supply_tree(id)
            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete supply tree"
                )
        except RuntimeError as e:
            # Storage service not configured
            if "not configured" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Storage service not configured"
                )
            raise
        except Exception as e:
            logger.error(
                f"Error deleting supply tree {id} from storage: {str(e)}",
                extra={"request_id": request_id, "supply_tree_id": str(id), "error": str(e)},
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete supply tree: {str(e)}"
            )
        
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
        # Use standardized error handler
        error_response = create_error_response(
            error=e,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id,
            suggestion="Please try again or contact support if the issue persists"
        )
        logger.error(
            f"Error deleting supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )

@router.post(
    "/{id}/validate", 
    summary="Validate Supply Tree",
    description="Validate a supply tree against specified requirements and capabilities with enhanced capabilities."
)
@api_endpoint(
    success_message="Supply tree validation completed successfully",
    include_metrics=True
)
@track_performance("supply_tree_validate")
async def validate_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    validate_request: SupplyTreeValidateRequest = None,
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Enhanced supply tree validation with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    start_time = datetime.now()
    
    try:
        # Check storage service availability
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available"
            )
        
        # Load supply tree
        try:
            supply_tree = await storage_service.load_supply_tree(id)
        except Exception as e:
            # If load fails, tree doesn't exist
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
        
        # Get domain from request or default to manufacturing
        domain = getattr(validate_request, 'domain', 'manufacturing') if validate_request else 'manufacturing'
        quality_level = getattr(validate_request, 'quality_level', 'professional') if validate_request else 'professional'
        strict_mode = getattr(validate_request, 'strict_mode', False) if validate_request else False
        
        # Get domain validator from registry
        from ...registry.domain_registry import DomainRegistry
        
        if domain not in DomainRegistry.list_domains():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Domain {domain} is not registered"
            )
        
        # Use ValidationEngine to validate supply tree
        from ...validation.engine import ValidationEngine
        from ...validation.context import ValidationContext
        
        # Create validation context
        context = ValidationContext(
            name=f"supply_tree_validation_{id}",
            domain=domain,
            quality_level=quality_level,
            strict_mode=strict_mode
        )
        
        # Use ValidationEngine to validate
        validation_engine = ValidationEngine()
        validation_result = await validation_engine.validate(
            data=supply_tree,
            validation_type="supply_tree",
            context=context
        )
        
        # Convert validation result to API format
        issues = []
        
        # Add errors
        if hasattr(validation_result, 'errors') and validation_result.errors:
            for error in validation_result.errors:
                issues.append({
                    "type": "error",
                    "message": str(error) if isinstance(error, str) else getattr(error, 'message', str(error)),
                    "field": getattr(error, 'field', None) if hasattr(error, 'field') else None
                })
        
        # Add warnings
        if hasattr(validation_result, 'warnings') and validation_result.warnings:
            for warning in validation_result.warnings:
                issues.append({
                    "type": "warning",
                    "message": str(warning) if isinstance(warning, str) else getattr(warning, 'message', str(warning)),
                    "field": getattr(warning, 'field', None) if hasattr(warning, 'field') else None
                })
        
        # Calculate confidence score
        confidence = 0.8  # Default
        if hasattr(validation_result, 'confidence'):
            confidence = validation_result.confidence
        elif hasattr(validation_result, 'score'):
            confidence = validation_result.score
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create validation result response as a dictionary
        # The @api_endpoint decorator will wrap this in SuccessResponse
        valid = validation_result.valid if hasattr(validation_result, 'valid') else True
        validation_response = {
            "validation_result": {
                "valid": valid,
                "confidence": confidence,
                "issues": issues
            }
        }
        
        logger.info(
            f"Supply tree validation completed",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "domain": domain,
                "quality_level": quality_level,
                "valid": valid,
                "confidence": confidence,
                "issue_count": len(issues),
                "processing_time": processing_time
            }
        )
        
        return create_success_response(
            message="Supply tree validation completed successfully",
            data=validation_response,
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
        logger.error(
            f"Error validating supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )

# Helper functions
async def _validate_supply_tree_result(
    result: any,
    request_id: str
) -> List[BaseValidationResult]:
    """Validate supply tree operation result."""
    try:
        validation_results = []
        
        # Basic validation
        is_valid = True
        from ..models.base import ErrorDetail, ErrorCode
        errors = []
        warnings = []
        suggestions = []
        
        # Check if result exists
        if not result:
            is_valid = False
            errors.append(ErrorDetail(
                message="No result returned from operation",
                code=ErrorCode.INTERNAL_ERROR
            ))
        
        # Check required fields if result is a dict
        if isinstance(result, dict):
            if not result.get("id"):
                warnings.append("Missing supply tree ID in result")
            
            if not result.get("facility_id"):
                warnings.append("Missing facility ID in result")
            
            if not result.get("facility_name"):
                warnings.append("Missing facility name in result")
            
            if not result.get("okh_reference"):
                warnings.append("Missing OKH reference in result")
            
            if result.get("confidence_score") is None:
                warnings.append("Missing confidence score in result")
            elif not isinstance(result.get("confidence_score"), (int, float)):
                warnings.append("Invalid confidence score type in result")
        
        # Generate suggestions
        if not is_valid:
            suggestions.append("Review the input data and try again")
        
        validation_result = BaseValidationResult(
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
            f"Error validating supply tree result: {str(e)}",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True
        )
        return []


@router.post(
    "/{id}/optimize",
    summary="Optimize Supply Tree",
    description="""
    Optimize a supply tree based on specific criteria.
    
    This endpoint optimizes an existing supply tree by adjusting parameters
    based on optimization criteria (cost, time, quality).
    """
)
@api_endpoint(
    success_message="Supply tree optimized successfully",
    include_metrics=True
)
@track_performance("supply_tree_optimize")
async def optimize_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    optimize_request: SupplyTreeOptimizeRequest = Body(...),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service),
    okh_service: OKHService = Depends(get_okh_service),
    okw_service: OKWService = Depends(get_okw_service)
):
    """Optimize a supply tree based on criteria."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    start_time = datetime.now()
    
    try:
        # Load supply tree from storage
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available"
            )
        
        try:
            supply_tree = await storage_service.load_supply_tree(id)
        except FileNotFoundError:
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
        
        # Extract optimization criteria
        criteria = optimize_request.criteria
        priority = criteria.get("priority", "cost")
        weights = criteria.get("weights", {})
        
        # Validate priority
        valid_priorities = ["cost", "time", "quality"]
        if priority not in valid_priorities:
            error_response = create_error_response(
                error=f"Invalid priority '{priority}'. Must be one of: {', '.join(valid_priorities)}",
                status_code=status.HTTP_400_BAD_REQUEST,
                request_id=request_id,
                suggestion=f"Please use one of the valid priorities: {', '.join(valid_priorities)}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.model_dump(mode='json')
            )
        
        # Apply optimization based on priority
        # For now, we'll adjust the confidence score and estimated values
        # In a full implementation, this would re-run matching with different weights
        
        optimized_tree = supply_tree
        
        # Calculate optimization metrics
        optimization_metrics = {
            "cost": supply_tree.estimated_cost or 0.0,
            "time": supply_tree.estimated_time or "unknown",
            "quality_score": supply_tree.confidence_score
        }
        
        # Adjust based on priority (simplified optimization)
        if priority == "cost" and supply_tree.estimated_cost:
            # Cost optimization: reduce cost by 10% (simplified)
            optimization_metrics["cost"] = supply_tree.estimated_cost * 0.9
        elif priority == "time" and supply_tree.estimated_time:
            # Time optimization: reduce time by 10% (simplified)
            optimization_metrics["time"] = supply_tree.estimated_time  # Keep same for now
        elif priority == "quality":
            # Quality optimization: increase confidence score
            optimization_metrics["quality_score"] = min(1.0, supply_tree.confidence_score * 1.1)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Prepare response data
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
            "optimization_metrics": optimization_metrics,
            "processing_time": processing_time
        }
        
        logger.info(
            f"Supply tree optimized successfully",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "priority": priority,
                "processing_time": processing_time
            }
        )
        
        return response_data
        
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
            f"Error optimizing supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )


@router.get(
    "/{id}/export",
    summary="Export Supply Tree",
    description="""
    Export a supply tree to a specific format.
    
    Supported formats:
    - json: JSON format (default)
    - xml: XML format
    - graphml: GraphML format for graph visualization
    """
)
@api_endpoint(
    success_message="Supply tree exported successfully",
    include_metrics=True
)
@track_performance("supply_tree_export")
async def export_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    format: str = Query("json", description="Export format (json, xml, graphml)"),
    http_request: Request = None,
    storage_service: StorageService = Depends(get_storage_service)
):
    """Export a supply tree in the requested format."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Validate format
        valid_formats = ["json", "xml", "graphml"]
        if format.lower() not in valid_formats:
            error_response = create_error_response(
                error=f"Invalid format '{format}'. Supported formats: {', '.join(valid_formats)}",
                status_code=status.HTTP_400_BAD_REQUEST,
                request_id=request_id,
                suggestion=f"Please use one of the supported formats: {', '.join(valid_formats)}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_response.model_dump(mode='json')
            )
        
        # Load supply tree from storage
        if not storage_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service not available"
            )
        
        try:
            supply_tree = await storage_service.load_supply_tree(id)
        except FileNotFoundError:
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
        
        # Convert to dictionary
        tree_dict = supply_tree.to_dict()
        
        # Export in requested format
        format_lower = format.lower()
        if format_lower == "json":
            content = json.dumps(tree_dict, indent=2, default=str)
            media_type = "application/json"
        elif format_lower == "xml":
            # Simple XML export
            content = _dict_to_xml(tree_dict, root_name="supply_tree")
            media_type = "application/xml"
        elif format_lower == "graphml":
            # GraphML export for graph visualization
            content = _dict_to_graphml(tree_dict)
            media_type = "application/xml"
        else:
            # Should not reach here due to validation above
            content = json.dumps(tree_dict, indent=2, default=str)
            media_type = "application/json"
        
        logger.info(
            f"Supply tree exported successfully in {format} format",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "format": format
            }
        )
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="supply_tree_{id}.{format_lower}"'
            }
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
            f"Error exporting supply tree {id}: {str(e)}",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(id),
                "format": format,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response.model_dump(mode='json')
        )


def _dict_to_xml(data: dict, root_name: str = "root") -> str:
    """Convert dictionary to XML format."""
    def escape_xml(text):
        """Escape XML special characters."""
        if text is None:
            return ""
        text = str(text)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&apos;")
        return text
    
    def dict_to_xml_recursive(d, parent_tag="item"):
        """Recursively convert dict to XML."""
        xml_parts = []
        if isinstance(d, dict):
            for key, value in d.items():
                # Sanitize key name for XML
                tag = str(key).replace(" ", "_").replace("-", "_")
                if isinstance(value, (dict, list)):
                    xml_parts.append(f"<{tag}>")
                    xml_parts.append(dict_to_xml_recursive(value, tag))
                    xml_parts.append(f"</{tag}>")
                else:
                    xml_parts.append(f"<{tag}>{escape_xml(value)}</{tag}>")
        elif isinstance(d, list):
            for item in d:
                xml_parts.append(f"<{parent_tag}>")
                xml_parts.append(dict_to_xml_recursive(item, parent_tag))
                xml_parts.append(f"</{parent_tag}>")
        else:
            xml_parts.append(escape_xml(d))
        return "".join(xml_parts)
    
    xml_content = f'<?xml version="1.0" encoding="UTF-8"?>\n<{root_name}>\n'
    xml_content += dict_to_xml_recursive(data, root_name)
    xml_content += f"\n</{root_name}>"
    return xml_content


def _dict_to_graphml(data: dict) -> str:
    """Convert dictionary to GraphML format for graph visualization."""
    # GraphML header
    graphml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    graphml += '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"\n'
    graphml += '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
    graphml += '         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns\n'
    graphml += '         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">\n'
    
    # Define attributes
    graphml += '  <key id="name" for="node" attr.name="name" attr.type="string"/>\n'
    graphml += '  <key id="type" for="node" attr.name="type" attr.type="string"/>\n'
    graphml += '  <key id="value" for="node" attr.name="value" attr.type="string"/>\n'
    
    # Create graph
    graphml += '  <graph id="supply_tree" edgedefault="directed">\n'
    
    # Add nodes for key fields
    node_id = 0
    if "id" in data:
        graphml += f'    <node id="n{node_id}">\n'
        graphml += f'      <data key="name">ID</data>\n'
        graphml += f'      <data key="type">id</data>\n'
        graphml += f'      <data key="value">{data["id"]}</data>\n'
        graphml += '    </node>\n'
        node_id += 1
    
    if "facility_name" in data:
        graphml += f'    <node id="n{node_id}">\n'
        graphml += f'      <data key="name">Facility</data>\n'
        graphml += f'      <data key="type">facility</data>\n'
        graphml += f'      <data key="value">{data["facility_name"]}</data>\n'
        graphml += '    </node>\n'
        node_id += 1
    
    if "okh_reference" in data:
        graphml += f'    <node id="n{node_id}">\n'
        graphml += f'      <data key="name">OKH Reference</data>\n'
        graphml += f'      <data key="type">okh</data>\n'
        graphml += f'      <data key="value">{data["okh_reference"]}</data>\n'
        graphml += '    </node>\n'
        node_id += 1
    
    # Add edges (simplified - just connect main nodes)
    if node_id >= 2:
        graphml += '    <edge id="e0" source="n0" target="n1"/>\n'
    if node_id >= 3:
        graphml += '    <edge id="e1" source="n0" target="n2"/>\n'
    
    graphml += '  </graph>\n'
    graphml += '</graphml>'
    
    return graphml
