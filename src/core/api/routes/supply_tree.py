from fastapi import APIRouter, HTTPException, Query, Path, status, Request, Depends
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# Import new standardized components
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

# Import existing models (now properly used through inheritance)
from ..models.supply_tree.request import (
    SupplyTreeCreateRequest,
    SupplyTreeValidateRequest
)
from ..models.supply_tree.response import (
    SupplyTreeResponse,
    ValidationResult
)
from ...utils.logging import get_logger

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

# Enhanced request models that inherit from original models
class EnhancedSupplyTreeCreateRequest(SupplyTreeCreateRequest, BaseAPIRequest, LLMRequestMixin):
    """Enhanced supply tree creation request with standardized fields and LLM support."""
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflows": {
                    "pcb_assembly": {
                        "name": "PCB Assembly Workflow",
                        "nodes": {
                            "component_placement": {
                                "name": "Component Placement",
                                "okh_refs": ["electronics-manufacturing"],
                                "input_requirements": {"components": "list"},
                                "output_specifications": {"placed_components": "boolean"}
                            }
                        }
                    }
                },
                "connections": [],
                "okh_reference": "electronics-manufacturing",
                "required_quantity": 100,
                "deadline": "2024-12-31T23:59:59Z",
                "metadata": {"project": "IoT Sensor Node"},
                "use_llm": True,
                "llm_provider": "anthropic",
                "llm_model": "claude-3-sonnet",
                "quality_level": "professional",
                "strict_mode": False
            }
        }


class EnhancedSupplyTreeResponse(SupplyTreeResponse, SuccessResponse, LLMResponseMixin):
    """Enhanced supply tree response with standardized fields and LLM information."""
    
    # Additional fields for enhanced response
    processing_time: float = 0.0
    validation_results: Optional[List[BaseValidationResult]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "00000000-0000-0000-0000-000000000000",
                "workflows": {
                    "pcb_assembly": {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "name": "PCB Assembly Workflow",
                        "nodes": {},
                        "edges": [],
                        "entry_points": ["start"],
                        "exit_points": ["end"]
                    }
                },
                "creation_time": "2024-01-01T12:00:00Z",
                "confidence": 0.8,
                "required_quantity": 100,
                "connections": [],
                "snapshots": {},
                "okh_reference": "electronics-manufacturing",
                "deadline": "2024-12-31T23:59:59Z",
                "metadata": {"project": "IoT Sensor Node"},
                "status": "success",
                "message": "Supply tree operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789",
                "processing_time": 2.5,
                "llm_used": True,
                "llm_provider": "anthropic",
                "llm_cost": 0.025,
                "data": {},
                "validation_results": []
            }
        }

@router.post(
    "/create", 
    response_model=EnhancedSupplyTreeResponse, 
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
@validate_request(EnhancedSupplyTreeCreateRequest)
@track_performance("supply_tree_create")
@llm_endpoint(
    default_provider="anthropic",
    default_model="claude-3-sonnet",
    track_costs=True
)
async def create_supply_tree(
    request: EnhancedSupplyTreeCreateRequest,
    http_request: Request
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
    start_time = datetime.utcnow()
    
    try:
        # Create supply tree (placeholder implementation)
        supply_tree_id = UUID("00000000-0000-0000-0000-000000000000")
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Create enhanced response using the proper SupplyTreeResponse structure
        response_data = {
            "id": supply_tree_id,
            "workflows": request.workflows,
            "creation_time": "2023-01-01T00:00:00Z",
            "confidence": 0.8,
            "required_quantity": request.required_quantity,
            "connections": request.connections,
            "snapshots": {},
            "okh_reference": request.okh_reference,
            "deadline": request.deadline,
            "metadata": request.metadata,
            "processing_time": processing_time,
            "validation_results": await _validate_supply_tree_result({"id": str(supply_tree_id), "workflows": request.workflows}, request_id)
        }
        
        logger.info(
            f"Supply tree created successfully",
            extra={
                "request_id": request_id,
                "supply_tree_id": str(supply_tree_id),
                "processing_time": processing_time,
                "llm_used": request.use_llm
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
    response_model=EnhancedSupplyTreeResponse,
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
    response_model=EnhancedSupplyTreeResponse,
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
    request: EnhancedSupplyTreeCreateRequest = None,
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
            
            if not result.get("name"):
                warnings.append("Missing supply tree name in result")
            
            if not result.get("workflows"):
                warnings.append("Missing workflows in result")
        
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
