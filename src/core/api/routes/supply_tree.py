from fastapi import APIRouter, HTTPException, Query, Path, status, Request, Depends
from typing import Optional, List
from uuid import UUID
from datetime import datetime

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
    SupplyTreeValidateRequest
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
    response_model=SupplyTreeResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create Supply Tree",
    description="""
    Create a supply tree with enhanced capabilities.
    
    This endpoint provides:
    - Standardized request/response formats
    - LLM integration support
    - Enhanced error handling
    - Performance metrics
    - Comprehensive validation
    
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
    default_model="claude-3-sonnet",
    track_costs=True
)
async def create_supply_tree(
    request: SupplyTreeCreateRequest,
    http_request: Request,
    storage_service: StorageService = Depends(),
    okh_service: OKHService = Depends(),
    okw_service: OKWService = Depends()
):
    """
    Enhanced supply tree creation with standardized patterns.
    
    Args:
        request: Enhanced supply tree creation request with standardized fields
        http_request: HTTP request object for tracking
        
    Returns:
        Enhanced supply tree response with comprehensive data
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
        try:
            okh_manifest = await okh_service.get(UUID(request.okh_reference))
        except (ValueError, TypeError):
            # If okh_reference is not a valid UUID, treat it as a reference string
            pass
        
        # Create the supply tree using the factory method
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
        
        # Save the supply tree to storage
        if storage_service:
            await storage_service.save_supply_tree(supply_tree)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create response data using the consolidated model structure
        response_data = {
            "id": supply_tree.id,
            "facility_id": supply_tree.facility_id,
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
                "facility_id": str(supply_tree.facility_id),
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
            detail=error_response.model_dump()
        )

@router.get(
    "/{id}", 
    response_model=SupplyTreeResponse,
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
    http_request: Request = None
):
    """Enhanced supply tree retrieval with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Placeholder implementation - return 404 for now
        error_response = create_error_response(
            error=f"Supply tree with ID {id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
            suggestion="Please check the supply tree ID and try again"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump()
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
            detail=error_response.model_dump()
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
    - Comprehensive validation
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
    http_request: Request = None
):
    """Enhanced supply tree listing with pagination and metrics."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Placeholder implementation - return empty list
        results = []
        total_items = 0
        
        # Apply pagination
        start_idx = (pagination.page - 1) * pagination.page_size
        end_idx = start_idx + pagination.page_size
        paginated_results = results[start_idx:end_idx]
        
        # Create pagination info
        total_pages = (total_items + pagination.page_size - 1) // pagination.page_size
        
        return create_success_response(
            message="Supply trees listed successfully",
            data={
                "items": paginated_results,
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
            detail=error_response.model_dump()
        )

@router.put(
    "/{id}", 
    response_model=SupplyTreeResponse,
    summary="Update Supply Tree",
    description="Update an existing supply tree with enhanced capabilities."
)
@api_endpoint(
    success_message="Supply tree updated successfully",
    include_metrics=True
)
@track_performance("supply_tree_update")
async def update_supply_tree(
    id: UUID = Path(..., title="The ID of the supply tree"),
    request: SupplyTreeCreateRequest = None,
    http_request: Request = None
):
    """Enhanced supply tree update with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Placeholder implementation - return 404 for now
        error_response = create_error_response(
            error=f"Supply tree with ID {id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            request_id=request_id,
            suggestion="Please check the supply tree ID and try again"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response.model_dump()
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
            detail=error_response.model_dump()
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
    http_request: Request = None
):
    """Enhanced supply tree deletion with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Placeholder implementation
        return create_success_response(
            message=f"Supply tree with ID {id} deleted successfully",
            data={},
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
            detail=error_response.model_dump()
        )

@router.post(
    "/{id}/validate", 
    response_model=ValidationResult,
    summary="Validate Supply Tree",
    description="Validate a supply tree against specified requirements and capabilities with enhanced capabilities."
)
@api_endpoint(
    success_message="Supply tree validation completed successfully",
    include_metrics=True
)
@track_performance("supply_tree_validate")
async def validate_supply_tree(
    request: SupplyTreeValidateRequest,
    id: UUID = Path(..., title="The ID of the supply tree"),
    http_request: Request = None
):
    """Enhanced supply tree validation with standardized patterns."""
    request_id = getattr(http_request.state, 'request_id', None) if http_request else None
    
    try:
        # Placeholder implementation using the proper ValidationResult model
        validation_result = ValidationResult(
            valid=True,
            confidence=0.8,
            issues=[]
        )
        
        return create_success_response(
            message="Supply tree validation completed successfully",
            data={"validation_result": validation_result.model_dump()},
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
            detail=error_response.model_dump()
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
